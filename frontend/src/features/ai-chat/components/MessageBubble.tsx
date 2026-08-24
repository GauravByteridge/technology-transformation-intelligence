import type { ChatMessage } from '@/types';

interface MessageBubbleProps {
  message: ChatMessage;
}

/**
 * MessageBubble — Individual message display with role-based styling.
 * User messages are right-aligned with teal background.
 * Assistant messages are left-aligned with dark background and markdown rendering.
 */
export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isError = message.content.startsWith('Error:');

  const formattedTime = formatTimestamp(message.timestamp);
  const bubbleStyles = getBubbleStyles(isUser, isError);

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      role="listitem"
      aria-label={`${isUser ? 'You' : 'Assistant'} said`}
    >
      <div className={`max-w-[80%] rounded-lg px-4 py-3 ${bubbleStyles}`}>
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="text-sm leading-relaxed prose-dark">
            <MarkdownContent content={message.content} />
          </div>
        )}
        <time
          dateTime={message.timestamp}
          className={`mt-1.5 block text-xs ${isUser ? 'text-teal-200' : isError ? 'text-red-400' : 'text-gray-500'}`}
        >
          {formattedTime}
        </time>
      </div>
    </div>
  );
}

function getBubbleStyles(isUser: boolean, isError: boolean): string {
  if (isError) {
    return 'bg-red-500/10 border border-red-500/30 text-red-300';
  }
  if (isUser) {
    return 'bg-teal-600 text-white';
  }
  return 'bg-gray-800/80 text-gray-200 border border-gray-700/50';
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

// ---------------------------------------------------------------------------
// Lightweight Markdown Renderer (no external dependency)
// ---------------------------------------------------------------------------

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Tables (| col1 | col2 |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const row = lines[i].trim();
        // Skip separator rows (|---|---|)
        if (row.match(/^\|[\s\-:|]+\|$/)) {
          i++;
          continue;
        }
        const cells = row.split('|').slice(1, -1).map((c) => c.trim());
        tableRows.push(cells);
        i++;
      }
      if (tableRows.length > 0) {
        const header = tableRows[0];
        const body = tableRows.slice(1);
        elements.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-lg border border-gray-700/50">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-700/50 bg-gray-900/50">
                  {header.map((cell, ci) => (
                    <th key={ci} className="px-3 py-2 text-left font-medium text-gray-300">
                      <InlineMarkdown text={cell} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri} className="border-b border-gray-700/30 last:border-0">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3 py-2 text-gray-400">
                        <InlineMarkdown text={cell} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // Headers (### Header)
    const headerMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      const className = level === 1
        ? 'text-base font-semibold text-white mt-3 mb-1'
        : level === 2
          ? 'text-sm font-semibold text-white mt-3 mb-1'
          : 'text-sm font-medium text-gray-200 mt-2 mb-1';
      elements.push(
        <p key={i} className={className}>
          <InlineMarkdown text={text} />
        </p>
      );
      i++;
      continue;
    }

    // Unordered list items (* item or - item)
    if (line.match(/^\s*[\*\-]\s+/)) {
      const listItems: { text: string; key: number }[] = [];
      while (i < lines.length && lines[i].match(/^\s*[\*\-]\s+/)) {
        const itemText = lines[i].replace(/^\s*[\*\-]\s+/, '');
        listItems.push({ text: itemText, key: i });
        i++;
      }
      elements.push(
        <ul key={`list-${listItems[0].key}`} className="space-y-1 my-1.5 ml-1">
          {listItems.map((item) => (
            <li key={item.key} className="flex items-start gap-2 text-gray-300">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400/60 mt-1.5 shrink-0" />
              <span><InlineMarkdown text={item.text} /></span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list items (1. item)
    if (line.match(/^\s*\d+\.\s+/)) {
      const listItems: { text: string; key: number; num: string }[] = [];
      while (i < lines.length && lines[i].match(/^\s*\d+\.\s+/)) {
        const match = lines[i].match(/^\s*(\d+)\.\s+(.+)$/);
        if (match) {
          listItems.push({ text: match[2], key: i, num: match[1] });
        }
        i++;
      }
      elements.push(
        <ol key={`ol-${listItems[0].key}`} className="space-y-1 my-1.5 ml-1">
          {listItems.map((item) => (
            <li key={item.key} className="flex items-start gap-2 text-gray-300">
              <span className="text-teal-400/80 text-xs font-medium mt-0.5 shrink-0 w-4">{item.num}.</span>
              <span><InlineMarkdown text={item.text} /></span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Empty line → spacing
    if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />);
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={i} className="text-gray-300 my-0.5">
        <InlineMarkdown text={line} />
      </p>
    );
    i++;
  }

  return <>{elements}</>;
}

/** Renders inline markdown: **bold**, *italic*, `code`, [links] */
function InlineMarkdown({ text }: { text: string }) {
  // Process inline patterns
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    // Bold: **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Italic: *text* (but not **)
    const italicMatch = remaining.match(/(?<!\*)\*([^\*]+?)\*(?!\*)/);
    // Code: `text`
    const codeMatch = remaining.match(/`([^`]+?)`/);

    // Find the earliest match
    const matches = [
      boldMatch ? { match: boldMatch, type: 'bold' } : null,
      italicMatch ? { match: italicMatch, type: 'italic' } : null,
      codeMatch ? { match: codeMatch, type: 'code' } : null,
    ].filter(Boolean) as { match: RegExpMatchArray; type: string }[];

    if (matches.length === 0) {
      parts.push(<span key={keyIdx++}>{remaining}</span>);
      break;
    }

    // Sort by index position
    matches.sort((a, b) => (a.match.index ?? 0) - (b.match.index ?? 0));
    const earliest = matches[0];
    const idx = earliest.match.index ?? 0;

    // Text before the match
    if (idx > 0) {
      parts.push(<span key={keyIdx++}>{remaining.slice(0, idx)}</span>);
    }

    // The matched element
    const matchedText = earliest.match[1];
    if (earliest.type === 'bold') {
      parts.push(<strong key={keyIdx++} className="font-semibold text-white">{matchedText}</strong>);
    } else if (earliest.type === 'italic') {
      parts.push(<em key={keyIdx++} className="italic text-gray-200">{matchedText}</em>);
    } else if (earliest.type === 'code') {
      parts.push(
        <code key={keyIdx++} className="px-1 py-0.5 bg-gray-700 text-teal-300 rounded text-xs font-mono">
          {matchedText}
        </code>
      );
    }

    remaining = remaining.slice(idx + earliest.match[0].length);
  }

  return <>{parts}</>;
}
