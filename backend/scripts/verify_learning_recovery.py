"""Read-only application backup and isolated M08 migration recovery drill.

No original database is migrated, restored, dropped or used for functional/AI
testing. Private dumps stay ignored; only newly created recovery DBs are removed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
import psycopg
from psycopg import sql

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import m08_local as local

DOCKER=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/DockerDesktop/resources/bin/docker.exe'
PRIVATE=local.ROOT/'.publication-private/m08_2'


def connect(url,name=None,autocommit=False):
    return psycopg.connect(host='127.0.0.1',port=url.port or 5432,user=url.username,
        password=url.password,dbname=name or url.database,autocommit=autocommit)


def fingerprints(db,columns):
    result={}
    for table,names in columns.items():
        values=sql.SQL(',').join(sql.Identifier(c) for c in names)
        query=sql.SQL("SELECT count(*),md5(coalesce(string_agg(jsonb_build_array({cols})::text,'' ORDER BY jsonb_build_array({cols})::text),'')) FROM {table}").format(cols=values,table=sql.Identifier(table))
        result[table]=list(db.execute(query).fetchone())
    return result


def drill(environment):
    preview=environment=='preview'
    url=local.make_url(local.env['PREVIEW_DATABASE_URL' if preview else 'DATABASE_URL']).set(host='127.0.0.1',port=5433 if preview else 5432)
    expected_name='fluentloop_preview' if preview else 'fluentloop'
    if url.database!=expected_name:raise SystemExit('Unexpected source database; no operation performed.')
    container='fluentloop-preview-preview-db-1' if preview else 'fluentloop-db'
    name='fluentloop_m08_2_recovery_'+uuid4().hex[:10]
    PRIVATE.mkdir(exist_ok=True)
    folder=PRIVATE/'backups';folder.mkdir(exist_ok=True)
    archive=folder/f'{environment}-{name}.dump'
    created=False
    def checked(args,**kwargs):
        result=subprocess.run(args,stderr=subprocess.PIPE,**kwargs)
        if result.returncode:
            # Do not print process arguments, connection URLs or SQL row values.
            raise RuntimeError('Recovery verification subprocess failed; private backup retained. No source DB was changed.')
        return result
    report={'environment':environment,'backup_file':str(archive),'source_modified':False}
    try:
        with connect(url) as source:
            source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            version=source.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            if version!='20261104_0008':raise RuntimeError('This drill expects the inspected unchanged 0008 application schema.')
            columns={}
            for table,column in source.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position"):
                columns.setdefault(table,[]).append(column)
            before=fingerprints(source,columns)
            snapshot=source.execute('SELECT pg_export_snapshot()').fetchone()[0]
            if not re.fullmatch(r'[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9A-Fa-f]+',snapshot):raise RuntimeError('Unexpected snapshot identifier.')
            with archive.open('xb') as out:
                checked([str(DOCKER),'exec',container,'sh','-c',
                    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --snapshot "$1"',
                    'snapshot',snapshot],stdout=out)
        with connect(url,'postgres',True) as admin:admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));created=True
        with archive.open('rb') as inp:
            checked([str(DOCKER),'exec','-i',container,'sh','-c',
                'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" --dbname "$1" --no-owner --no-privileges --exit-on-error',
                'restore',name],stdin=inp,stdout=subprocess.PIPE)
        with connect(url,name) as recovery:
            recovery.execute('SET TRANSACTION READ ONLY')
            restored=fingerprints(recovery,columns)
        if restored!=before:raise RuntimeError('Restored snapshot did not match its source fingerprint.')
        target=url.set(database=name).render_as_string(hide_password=False)
        checked([sys.executable,'-m','alembic','upgrade','20261104_0009'],cwd=local.ROOT/'backend',
            env={**os.environ,**local.env,'DATABASE_URL':target},stdout=subprocess.PIPE)
        with connect(url,name) as recovery:
            recovery.execute('SET TRANSACTION READ ONLY')
            migrated=fingerprints(recovery,columns)
            # The revision row is intentionally the only old-column change.
            changed=[t for t in before if t!='alembic_version' and migrated[t]!=before[t]]
            revision=recovery.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        if changed or revision!='20261104_0009':raise RuntimeError('Migration preservation comparison failed.')
        report.update(restore_verified=True,migration_verified=True,source_revision=version,recovery_revision=revision,
            application_tables_verified=len(columns)-1,changed_application_tables=changed,backup_bytes=archive.stat().st_size)
    finally:
        if created:
            if not name.startswith('fluentloop_m08_2_recovery_') or name==url.database:raise RuntimeError('Unsafe recovery cleanup target.')
            with connect(url,'postgres',True) as admin:
                admin.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()',(name,))
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
            report['temporary_recovery_database_removed']=True
    (PRIVATE/f'recovery-{environment}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='backup_file'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',choices=('main','preview','all'),default='all')
    args=parser.parse_args()
    try:
        for item in ('main','preview') if args.environment=='all' else (args.environment,):drill(item)
    except Exception:
        print('Recovery drill failed. No original database was migrated/restored; inspect protected local artifacts.',file=sys.stderr)
        raise SystemExit(1)
