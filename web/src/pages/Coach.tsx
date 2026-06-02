import { KeyboardEvent, useMemo, useState } from 'react';
import { Button, H1, Stack, Text, TextInput } from '@/canvas';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

const quickPrompts = [
  'What is my current risk level?',
  'What is the riskiest period I have ever had?',
  'Compare spring 2024 to now',
  'What should I change this week?',
];

const cleanResponse = (text: string) => {
  return text
    .replace(/^\s*#+\s*/gm, '')
    .replace(/\*\*|\*|__|`/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

export default function Coach() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Ask me about any day or period. I will call your monitoring tools and answer from the data.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (override?: string) => {
    const trimmed = (override ?? input).trim();
    if (!trimmed || loading) return;

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: trimmed }];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/coach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmed,
          history: nextMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.error ?? 'Request failed');
      }

      const reply = cleanResponse(payload.reply ?? '');
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${(error as Error).message}. Ensure the API server is running and an API key is configured.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onQuickPrompt = (prompt: string) => {
    if (loading) return;
    setInput(prompt);
    void sendMessage(prompt);
  };

  const renderedMessages = useMemo(
    () =>
      messages.map((message, index) => (
        <div
          key={`${message.role}-${index}`}
          className={`chat-bubble ${message.role === 'user' ? 'user' : 'assistant'}`}
        >
          <div className="chat-text">{message.content}</div>
        </div>
      )),
    [messages],
  );

  return (
    <Stack gap={20}>
      <H1>Coach (live)</H1>
      <Text tone="secondary" size="small">
        Ask questions about your monitoring data. Answers are grounded in local scores and retrieved context.
      </Text>

      <div className="chat-shell">
        <div className="chat-panel">
          <div className="chat-header">
            <div>
              <Text size="small" tone="secondary">Grounded coaching</Text>
              <h2>Athlete Coach</h2>
            </div>
            <Text size="small" tone="secondary">API status: {loading ? 'Working' : 'Ready'}</Text>
          </div>

          <div className="chat-messages">
            {renderedMessages}
            {loading ? (
              <div className="chat-bubble assistant">
                <Text>Thinking…</Text>
              </div>
            ) : null}
          </div>

          <div className="chat-input">
            <TextInput
              value={input}
              onChange={setInput}
              placeholder="Ask: Why was May 15 flagged at 72 km?"
              onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
                if (event.key === 'Enter') {
                  void sendMessage();
                }
              }}
            />
            <Button onClick={() => void sendMessage()} disabled={loading || !input.trim()}>
              {loading ? 'Working…' : 'Send'}
            </Button>
          </div>
        </div>

        <div className="side-panel">
          <div className="hint-card">
            <h3>Quick prompts</h3>
            <div className="quick-prompts">
              {quickPrompts.map((prompt) => (
                <button key={prompt} className="chip primary" onClick={() => onQuickPrompt(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="hint-card">
            <h3>What you’ll get</h3>
            <ul>
              <li>Specific dates and scores from your monitoring data</li>
              <li>Which tracks agree or disagree</li>
              <li>Clear next step for volume or recovery</li>
            </ul>
          </div>

          <div className="hint-card">
            <h3>Example</h3>
            <ul>
              <li>Why was May 15 flagged at 72 km?</li>
              <li>Compare spring 2024 to now</li>
              <li>What if I cut volume by 15%?</li>
            </ul>
          </div>
        </div>
      </div>
    </Stack>
  );
}
