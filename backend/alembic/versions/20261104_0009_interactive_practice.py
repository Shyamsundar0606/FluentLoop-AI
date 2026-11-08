"""M08 additive structured exercises and unified focused-practice sessions.

Existing answer UUID strings, snapshots, scores and identifiers are retained.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261104_0009"
down_revision = "20261104_0008"
branch_labels = None
depends_on = None


def upgrade():
    # Revision 0003 uses live ORM metadata on a fresh install. Inspect only the
    # additions here so both that path and a genuine pre-M08 schema upgrade work.
    inspector=sa.inspect(op.get_bind())
    columns={table:{c['name'] for c in inspector.get_columns(table)}
             for table in ('exercises','grammar_topics','exercise_attempts','learning_sessions')}
    def add(table,column):
        if column.name not in columns[table]:op.add_column(table,column)
    for fk in inspector.get_foreign_keys('exercises'):
        if fk['constrained_columns'] in (['learning_objective_id'],['grammar_topic_id']):
            op.drop_constraint(fk['name'],'exercises',type_='foreignkey')

    add('exercises', sa.Column('exercise_data', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    add('exercises', sa.Column('learning_objective_id', sa.Uuid(), nullable=True))
    add('exercises', sa.Column('grammar_topic_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_exercise_objective', 'exercises', 'learning_objectives', ['learning_objective_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_exercise_grammar', 'exercises', 'grammar_topics', ['grammar_topic_id'], ['id'], ondelete='RESTRICT')
    op.drop_constraint('ck_exercises_type', 'exercises', type_='check')
    op.create_check_constraint('ck_exercises_type', 'exercises', "exercise_type IN ('multiple_choice','translation','fill_blank','matching','sentence_order','short_answer','listening')")
    add('grammar_topics', sa.Column('publication_status', sa.String(24), nullable=False, server_default='inherited'))
    add('grammar_topics', sa.Column('teaching_metadata', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    if 'ck_grammar_topic_publication' in {c['name'] for c in inspector.get_check_constraints('grammar_topics')}:
        op.drop_constraint('ck_grammar_topic_publication','grammar_topics',type_='check')
    op.create_check_constraint('ck_grammar_topic_publication', 'grammar_topics', "publication_status IN ('inherited','draft','review','published','retired')")
    add('exercise_attempts', sa.Column('answer_payload', JSONB(), nullable=True))
    add('learning_sessions', sa.Column('activity_key', sa.String(128), nullable=False, server_default='lesson'))
    # The old uniqueness is retained for every legacy row (activity_key=lesson).
    # A focused practice session can coexist without being counted as a lesson.
    op.drop_index('uq_learning_sessions_active_user_lesson', table_name='learning_sessions')
    op.create_index('uq_learning_sessions_active_user_lesson', 'learning_sessions', ['user_id','lesson_id','activity_key'],
                    unique=True, postgresql_where=sa.text("status = 'in_progress'"))


def downgrade():
    db=op.get_bind()
    # Never silently discard new-format responses or mislabel practice history.
    used=db.execute(sa.text("SELECT EXISTS(SELECT 1 FROM exercise_attempts WHERE answer_payload IS NOT NULL AND answer_payload <> 'null'::jsonb) OR EXISTS(SELECT 1 FROM learning_sessions WHERE activity_key <> 'lesson') OR EXISTS(SELECT 1 FROM exercises WHERE exercise_data <> '{}'::jsonb OR learning_objective_id IS NOT NULL OR grammar_topic_id IS NOT NULL) OR EXISTS(SELECT 1 FROM grammar_topics WHERE teaching_metadata <> '{}'::jsonb OR publication_status <> 'inherited')" )).scalar()
    if used:
        raise RuntimeError('M08 data exists; downgrade blocked to preserve structured answers and practice history.')
    op.drop_index('uq_learning_sessions_active_user_lesson', table_name='learning_sessions')
    op.create_index('uq_learning_sessions_active_user_lesson', 'learning_sessions', ['user_id','lesson_id'], unique=True, postgresql_where=sa.text("status = 'in_progress'"))
    op.drop_column('learning_sessions','activity_key')
    op.drop_column('exercise_attempts','answer_payload')
    op.drop_constraint('ck_grammar_topic_publication','grammar_topics',type_='check')
    op.drop_column('grammar_topics','teaching_metadata')
    op.drop_column('grammar_topics','publication_status')
    op.drop_constraint('ck_exercises_type','exercises',type_='check')
    op.create_check_constraint('ck_exercises_type','exercises',"exercise_type IN ('multiple_choice','translation','fill_blank','matching','sentence_order','short_answer')")
    op.drop_constraint('fk_exercise_objective','exercises',type_='foreignkey')
    op.drop_constraint('fk_exercise_grammar','exercises',type_='foreignkey')
    for name in ('grammar_topic_id','learning_objective_id','exercise_data'):
        op.drop_column('exercises',name)
