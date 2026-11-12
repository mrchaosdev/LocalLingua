import type {Caption} from './types';

export function mergeCaption(old: Caption[], incoming: Caption): Caption[] {
  const family = incoming.phase.split('.')[0];
  const index = old.findIndex(x => x.utterance_id === incoming.utterance_id && x.phase.split('.')[0] === family);
  if (index >= 0 && (old[index].is_final || incoming.revision <= old[index].revision)) return old;
  const next = [...old];
  const first=old.find(x=>x.utterance_id===incoming.utterance_id);
  const ordered={...incoming,utterance_order_ms:first?.utterance_order_ms??first?.created_at_ms??incoming.created_at_ms};
  if (index >= 0) next[index] = ordered;
  else next.push(ordered);
  next.sort((a,b)=>(a.utterance_order_ms??a.created_at_ms)-(b.utterance_order_ms??b.created_at_ms));
  return next.slice(-140);
}
