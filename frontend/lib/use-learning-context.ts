'use client';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { isFrenchLevel, type FrenchLevel } from './learning-levels';

export function useLearningContext() {
  const query=useSearchParams();const router=useRouter();const path=usePathname();const {user}=useAuth();
  const requested=(query.get('level')??'').toLowerCase();
  const level:FrenchLevel=isFrenchLevel(requested)?requested:user&&isFrenchLevel(user.preferences.current_level)?user.preferences.current_level:'a1';
  function setLevel(value:FrenchLevel){const next=new URLSearchParams(query.toString());next.set('level',value);next.delete('lesson');next.delete('topic');router.replace(`${path}?${next}`,{scroll:false});}
  const lesson=query.get('lesson')??undefined;
  const lessonId=lesson&&/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(lesson)?lesson:undefined;
  return {level,setLevel,lessonId,category:query.get('category')};
}
