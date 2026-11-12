import type {Caption} from './types';

export function mergeCaption(old: Caption[], incoming: Caption): Caption[] {
  const family = incoming.phase.split('.')[0];
  const index = old.findIndex(x => x.utterance_id === incoming.utterance_id && x.phase.split('.')[0] === family);
  if (index >= 0 && (old[index].is_final || incoming.revision <= old[index].revision)) return old;
  const next = [...old];
  if (index >= 0) next[index] = incoming;
  else next.push(incoming);
  return next.slice(-140);
}
