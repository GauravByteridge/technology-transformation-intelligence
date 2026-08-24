import { useMemo } from 'react';
import type { QueryHistoryEntry } from '@/types';

interface QueryHistoryProps {
  history: QueryHistoryEntry[];
  onSelectConversation: (conversationId: string) => void;
}

interface ConversationGroup {
  conversationId: string;
  entries: QueryHistoryEntry[];
  latestTimestamp: string;
}

/**
 * QueryHistory — Sidebar list of previous queries grouped by conversation.
 * Shows question text and timestamp for each entry.
 * Entries are grouped by conversation_id with clickable conversation headers.
 */
export function QueryHistory({ history, onSelectConversation }: QueryHistoryProps) {
  const groups = useMemo(() => groupByConversation(history), [history]);

  if (groups.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-400" role="status">
        No query history yet
      </div>
    );
  }

  return (
    <nav aria-label="Query history" className="flex flex-col overflow-y-auto">
      <h3 className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        History
      </h3>
      <ul className="space-y-1 px-2">
        {groups.map((group) => (
          <li key={group.conversationId}>
            <button
              type="button"
              onClick={() => onSelectConversation(group.conversationId)}
              className="w-full rounded-md px-3 py-2 text-left transition-colors hover:bg-gray-700/50 focus:bg-gray-700/50 focus:outline-none"
              aria-label={`Conversation: ${group.entries[0]?.question ?? 'Unknown'}`}
            >
              <p className="truncate text-sm font-medium text-gray-200">
                {group.entries[0]?.question ?? 'Untitled conversation'}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">
                {formatHistoryTimestamp(group.latestTimestamp)}
                {group.entries.length > 1 && (
                  <span className="ml-1">· {group.entries.length} messages</span>
                )}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function groupByConversation(history: QueryHistoryEntry[]): ConversationGroup[] {
  const groupMap = new Map<string, QueryHistoryEntry[]>();

  for (const entry of history) {
    const existing = groupMap.get(entry.conversation_id);
    if (existing) {
      existing.push(entry);
    } else {
      groupMap.set(entry.conversation_id, [entry]);
    }
  }

  const groups: ConversationGroup[] = [];
  for (const [conversationId, entries] of groupMap) {
    // Entries within a group sorted by timestamp ascending (oldest first)
    const sorted = [...entries].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
    const latestTimestamp = sorted[sorted.length - 1]?.timestamp ?? '';
    groups.push({ conversationId, entries: sorted, latestTimestamp });
  }

  // Groups sorted by most recent activity (descending)
  groups.sort(
    (a, b) => new Date(b.latestTimestamp).getTime() - new Date(a.latestTimestamp).getTime(),
  );

  return groups;
}

function formatHistoryTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return '';
  }
}
