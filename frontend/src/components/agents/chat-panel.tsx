import { useEffect, useMemo, useRef, useState } from 'react'
import { ShellLogo } from '@/components/shell-logo'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Loader2, Send, Sparkles, AlertCircle, Mic, Square, Car, Volume2, Paperclip, X, FileText, File as FileIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { agents } from '@/lib/api'
import type { Agent, AgentMessage, ChatAttachmentMeta } from '@/lib/api'
import { streamChat, type AgentStreamEvent } from '@/lib/agents-stream'
import { Markdown } from '@/components/agents/markdown'
import { ProposalCard, isProposalData, isProposalToolName } from '@/components/agents/proposal-card'
import { useSpeechRecognition } from '@/hooks/use-speech-recognition'
import { useSpeechSynthesis } from '@/hooks/use-speech-synthesis'
import { toSpeechText } from '@/lib/speech-text'
import { cn } from '@/lib/utils'

interface Props {
  agent: Agent
  conversationId: string | null
  onConversationCreated: (id: string) => void
  // Bumped by the parent on every sidebar interaction (new + select an
  // already-active conversation). Lets the chat input refocus even when
  // conversationId itself doesn't change.
  focusSignal?: number
  // Optional snapshot of the current page (route, label, filters,
  // selection). Forwarded as `page_context` on every streamChat call so
  // the agent can reason about "this row" / "the filters above".
  // Re-read on each send so we always pick up the latest state.
  getPageContext?: () => Record<string, unknown> | null
}

interface DraftMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  tools: { name: string; args: Record<string, unknown>; result?: { ok?: boolean; data?: unknown; text?: string | null } }[]
  error?: string
  pending?: boolean
  attachments?: StagedAttachment[]
}

/** A file the user picked, from the moment it's selected through upload.
 * `previewUrl` (images only) is a local blob: URL from the File object
 * itself — no round trip needed just to show a thumbnail pre-send.
 * `id` is filled in once the upload finishes; until then `uploading` is
 * true and the chip shows a spinner instead of a remove button. */
interface StagedAttachment {
  localId: string
  id: string | null
  filename: string
  mime: string
  size_bytes: number
  previewUrl: string | null
  uploading: boolean
  error?: string
}

const ACCEPTED_ATTACHMENT_TYPES = 'image/png,image/jpeg,image/webp,image/gif,application/pdf'

export function ChatPanel({ agent, conversationId, onConversationCreated, focusSignal, getPageContext }: Props) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [draft, setDraft] = useState<DraftMessage | null>(null) // assistant turn currently being streamed
  const [pendingUser, setPendingUser] = useState<DraftMessage | null>(null) // user msg shown immediately
  // Last error from a chat round, kept after streaming ends so the user
  // can actually see what went wrong. Cleared when they send a new message.
  const [lastError, setLastError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [staged, setStaged] = useState<StagedAttachment[]>([])
  const speech = useSpeechRecognition('pt-BR')
  const synth = useSpeechSynthesis('pt-BR')
  // Whether the user is "pinned" to the bottom of the scroll area. We
  // only auto-scroll while pinned — if the user scrolls up to read,
  // streaming deltas no longer yank them back down.
  const isAtBottomRef = useRef(true)

  // Hands-free loop (mic in car icon): listen → auto-send on silence →
  // speak the reply → listen again, until the user taps it off. Mirrored
  // into a ref because the streamChat callbacks and the speech-recognition
  // effect below close over stale state otherwise.
  const [voiceMode, setVoiceMode] = useState(false)
  const voiceModeRef = useRef(false)
  const prevListeningRef = useRef(false)
  const setVoiceModeActive = (on: boolean) => {
    voiceModeRef.current = on
    setVoiceMode(on)
  }

  const exitVoiceMode = () => {
    setVoiceModeActive(false)
    speech.stop()
    synth.stop()
  }

  const toggleVoiceMode = () => {
    if (voiceMode) {
      exitVoiceMode()
      return
    }
    setVoiceModeActive(true)
    speech.start()
  }

  // Recognition naturally stops after a pause (continuous=false) — that's
  // our cue to auto-send whatever was captured, or to just listen again if
  // it stopped on pure silence (no-speech timeout, stray mic bump, etc).
  useEffect(() => {
    const wasListening = prevListeningRef.current
    prevListeningRef.current = speech.listening
    if (!wasListening || speech.listening) return
    if (!voiceModeRef.current || streaming || synth.speaking) return
    const text = speech.transcript.trim()
    if (text) {
      send(text)
    } else {
      speech.start()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speech.listening])

  // Stop everything on unmount (switching agents/conversations remounts
  // this component via the `key={activeAgent.id}` in both chat surfaces).
  useEffect(() => {
    return () => {
      speech.stop()
      synth.stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const { data: history } = useQuery({
    queryKey: ['agent-conv-messages', conversationId],
    queryFn: () => (conversationId ? agents.conversations.messages(conversationId) : Promise.resolve([])),
    enabled: !!conversationId,
    staleTime: 1000 * 5,
  })

  // Snap to bottom when the conversation switches (it should look fresh)
  // and move keyboard focus to the input — covers both "+" (null) and
  // selecting an existing conversation. focusSignal also triggers focus
  // when the user clicks "+" while already on a null conversation.
  useEffect(() => {
    if (scrollRef.current) {
      isAtBottomRef.current = true
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
    inputRef.current?.focus()
  }, [conversationId, focusSignal])

  // Clear any stale optimistic draft when the conversation prop changes
  // for a reason OTHER than the in-flight stream getting its id assigned
  // (i.e. user picked a different thread from history, or hit "+"). We
  // detect "stream is mid-flight" via the `streaming` flag — during that
  // window the conversationId may legitimately go from null → real, and
  // we don't want to wipe the loading bubble. Once the stream finishes,
  // the existing finally{} clears the draft anyway.
  useEffect(() => {
    if (!streaming) {
      setDraft(null)
      setPendingUser(null)
      setLastError(null)
      setStaged((prev) => {
        prev.forEach((s) => s.previewUrl && URL.revokeObjectURL(s.previewUrl))
        return []
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId])

  // Mirror the live transcript into the input while listening, so the
  // user sees their words appear as they speak. They can still edit
  // before sending — recognition never auto-sends.
  useEffect(() => {
    if (speech.listening) setInput(speech.transcript)
  }, [speech.transcript, speech.listening])

  // Reset the textarea's inline height when the input is cleared (after
  // send, on conversation change, etc.) — onChange's auto-grow leaves
  // an explicit `style.height` behind that won't shrink on its own.
  useEffect(() => {
    if (input === '' && inputRef.current) {
      inputRef.current.style.height = ''
    }
  }, [input])

  // While streaming or new content arrives, only follow if pinned.
  useEffect(() => {
    if (!scrollRef.current) return
    if (isAtBottomRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [history, draft, pendingUser])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    // 80px tolerance — close enough to count as "at the bottom".
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight
    isAtBottomRef.current = distance < 80
  }

  // Upload starts the instant a file is picked (not deferred to send) so
  // the user sees progress/errors right away instead of at send time.
  const onFilesSelected = (files: FileList | null) => {
    if (!files || files.length === 0) return
    for (const file of Array.from(files)) {
      const localId = crypto.randomUUID()
      const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : null
      setStaged((prev) => [
        ...prev,
        { localId, id: null, filename: file.name, mime: file.type, size_bytes: file.size, previewUrl, uploading: true },
      ])
      agents.attachments
        .upload(agent.id, file)
        .then((meta: ChatAttachmentMeta) => {
          setStaged((prev) => prev.map((s) => (s.localId === localId ? { ...s, id: meta.id, uploading: false } : s)))
        })
        .catch((err: unknown) => {
          const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
            ?? (err instanceof Error ? err.message : t('agents.chat.attachmentUploadFailed', 'Upload failed'))
          setStaged((prev) => prev.map((s) => (s.localId === localId ? { ...s, uploading: false, error: message } : s)))
        })
    }
  }

  const removeStaged = (localId: string) => {
    setStaged((prev) => {
      const item = prev.find((s) => s.localId === localId)
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl)
      if (item?.id) agents.attachments.remove(agent.id, item.id).catch(() => {})
      return prev.filter((s) => s.localId !== localId)
    })
  }

  const send = async (overrideText?: string) => {
    const trimmed = (overrideText ?? input).trim()
    if (streaming) return
    // A photo/PDF with no caption is a valid message on its own — only
    // block when there's neither text nor any (successfully uploaded)
    // attachment to send.
    const readyAttachments = staged.filter((s) => s.id && !s.uploading)
    if (!trimmed && readyAttachments.length === 0) return
    // Still-uploading files: make the user wait rather than silently
    // sending without them.
    if (staged.some((s) => s.uploading)) return
    setInput('')
    setLastError(null)
    setStreaming(true)
    const sentAttachments = staged
    setStaged([])
    // User just took an action — they want to see the response.
    isAtBottomRef.current = true
    let errorThisTurn: string | null = null
    // Assembled outside React state so the voice-mode TTS step below has
    // the exact final text without racing setDraft's async updates.
    let assembledText = ''
    // Track the active conversation id locally — the React state for it
    // updates asynchronously, so a closure over `conversationId` still
    // sees the value at the start of send() and would invalidate the
    // wrong query key on a brand-new conversation.
    let activeConvId = conversationId
    // Remember whether this round started a fresh conversation, so we
    // can ask the backend to generate a real title from the LLM after
    // streaming completes successfully.
    const startedFresh = !conversationId
    const localId = crypto.randomUUID()
    setPendingUser({ id: 'pending-user-' + localId, role: 'user', text: trimmed, tools: [], attachments: sentAttachments })
    setDraft({ id: 'draft-' + localId, role: 'assistant', text: '', tools: [], pending: true })
    try {
      await streamChat({
        agentId: agent.id,
        content: trimmed,
        conversationId,
        pageContext: getPageContext?.() ?? null,
        attachmentIds: readyAttachments.map((s) => s.id as string),
        onEvent: (ev: AgentStreamEvent) => {
          if (ev.kind === 'conversation') {
            activeConvId = ev.conversation_id
            if (!conversationId) onConversationCreated(ev.conversation_id)
            return
          }
          if (ev.kind === 'text_delta') {
            assembledText += ev.text
            setDraft((d) => (d ? { ...d, text: d.text + ev.text } : d))
          } else if (ev.kind === 'tool_call') {
            setDraft((d) => (d ? { ...d, tools: [...d.tools, { name: ev.tool_name, args: ev.tool_args }] } : d))
          } else if (ev.kind === 'tool_result') {
            setDraft((d) => {
              if (!d) return d
              const idx = d.tools.findIndex((t) => t.name === ev.tool_name && !t.result)
              if (idx === -1) return d
              const copy = [...d.tools]
              copy[idx] = { ...copy[idx], result: ev.tool_result }
              return { ...d, tools: copy }
            })
          } else if (ev.kind === 'error') {
            errorThisTurn = `${ev.error_code || 'error'}: ${ev.error_message || ''}`
            setDraft((d) => (d ? { ...d, error: errorThisTurn || undefined } : d))
          } else if (ev.kind === 'done') {
            setDraft((d) => (d ? { ...d, pending: false } : d))
          }
        },
      })
    } catch (err) {
      errorThisTurn = String(err)
      setDraft((d) => (d ? { ...d, error: String(err) } : d))
    } finally {
      setStreaming(false)
      // Pull the persisted turn for the conversation we actually wrote
      // to. refetchQueries waits for the data to come back; only THEN do
      // we clear the optimistic draft so the user never sees a blank gap.
      if (activeConvId) {
        try {
          await qc.refetchQueries({ queryKey: ['agent-conv-messages', activeConvId] })
        } catch {
          // ignore — we still want to clear the draft below
        }
      }
      qc.invalidateQueries({ queryKey: ['agent-conversations'] })
      setPendingUser(null)
      setDraft(null)
      sentAttachments.forEach((s) => s.previewUrl && URL.revokeObjectURL(s.previewUrl))
      if (errorThisTurn) setLastError(errorThisTurn)
      // After the very first round of a brand-new conversation, ask the
      // backend to summarize the exchange into a short title via the
      // LLM. Fire-and-forget — the conversations list will refetch when
      // it lands.
      if (!errorThisTurn && startedFresh && activeConvId) {
        agents.conversations
          .generateTitle(activeConvId)
          .then(() => qc.invalidateQueries({ queryKey: ['agent-conversations'] }))
          .catch(() => {})
      }
      // Voice mode: read the reply aloud, then listen for the next turn.
      // Silent no-op if the user toggled voice mode off mid-response.
      if (voiceModeRef.current) {
        if (!errorThisTurn && assembledText.trim()) {
          synth.speak(toSpeechText(assembledText), () => {
            if (voiceModeRef.current) speech.start()
          })
        } else {
          speech.start()
        }
      }
    }
  }

  return (
    // min-h-0 is required so the inner flex-1 messages area can scroll
    // instead of pushing the input footer past the bottom of the viewport.
    <div className="flex flex-col h-full min-h-0">
      <div ref={scrollRef} onScroll={handleScroll} className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-4">
        {/* Empty state for a fresh conversation: brand mark + a few
            randomized suggestion chips so the user has something to
            click instead of staring at a blank panel. Hidden once any
            history / pending bubble / draft exists. */}
        {(history ?? []).length === 0 && !pendingUser && !draft && (
          <ChatEmptyState
            agent={agent}
            onPick={(text) => {
              setInput(text)
              // Defer focus so the textarea picks up the new value
              // before we drop the caret into it.
              requestAnimationFrame(() => inputRef.current?.focus())
            }}
          />
        )}
        <HistoryView agent={agent} history={history ?? []} />
        {/* `pendingUser` is the optimistic bubble shown the instant the
            user hits send. As soon as the SSE `conversation` event fires
            for a brand-new chat, the parent updates conversationId and
            the history query refetches — at which point the persisted
            user message lands in `history` while the optimistic bubble
            is still mounted, briefly duplicating the message. Suppress
            the optimistic bubble once history already contains a
            matching user message. */}
        {pendingUser &&
          !(history ?? []).some(
            (m) => m.role === 'user' && (m.content ?? '').trim() === pendingUser.text.trim(),
          ) && (
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-lg px-3 py-2 bg-primary text-primary-foreground">
              {!!pendingUser.attachments?.length && (
                <div className="flex flex-wrap gap-1.5 mb-1.5">
                  {pendingUser.attachments.map((a) => (
                    <StagedThumb key={a.localId} attachment={a} />
                  ))}
                </div>
              )}
              {pendingUser.text && <div className="whitespace-pre-wrap text-sm">{pendingUser.text}</div>}
            </div>
          </div>
        )}
        {draft && (
          <div className="space-y-2">
            {/* End users don't need to see raw tool-call traffic (which
                server queries ran, JSON payloads, etc) — only proposals,
                since those carry an Apply button and are a real decision
                the user needs to make. Everything else stays silent; the
                "thinking" spinner below is the only feedback while tools
                run with no visible text yet. */}
            {draft.tools.map((tool, i) => {
              const isProposal = isProposalToolName(tool.name) && !!tool.result?.data && isProposalData(tool.result.data)
              if (!isProposal) return null
              // Stable id for the localStorage "applied" marker — the
              // draft uses an in-flight uuid so we suffix with the index.
              return (
                <ProposalCard
                  key={i}
                  toolCallId={`draft-${draft.id}-${i}`}
                  data={tool.result!.data as Record<string, unknown>}
                />
              )
            })}
            {(draft.text || draft.pending) && (
              <div className="rounded-lg px-3 py-2 bg-muted">
                <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1 flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3" /> {agent.name}
                </div>
                {draft.text ? (
                  <Markdown>{draft.text + (draft.pending ? ' ▍' : '')}</Markdown>
                ) : (
                  <Loader2 className="inline h-3.5 w-3.5 animate-spin text-muted-foreground" />
                )}
              </div>
            )}
            {draft.error && (
              <div className="rounded-lg px-3 py-2 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-200 text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                {draft.error}
              </div>
            )}
          </div>
        )}
        {!draft && lastError && (
          <div className="rounded-lg px-3 py-2 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-200 text-sm flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1 break-words">{lastError}</div>
            <button
              type="button"
              onClick={() => setLastError(null)}
              className="text-xs uppercase tracking-wider text-rose-600/70 hover:text-rose-700 dark:text-rose-400/70 dark:hover:text-rose-200"
            >
              ✕
            </button>
          </div>
        )}
      </div>
      {voiceMode && (
        <div className="shrink-0 px-3 py-1.5 border-t bg-muted/50 flex items-center gap-1.5 text-xs text-muted-foreground">
          {synth.speaking ? (
            <>
              <Volume2 className="h-3.5 w-3.5 animate-pulse text-primary" />
              {t('agents.chat.voiceModeSpeaking', 'Speaking…')}
            </>
          ) : streaming ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {t('agents.chat.voiceModeThinking', 'Thinking…')}
            </>
          ) : (
            <>
              <Mic className="h-3.5 w-3.5 animate-pulse text-primary" />
              {t('agents.chat.voiceModeListening', 'Listening…')}
            </>
          )}
        </div>
      )}
      {staged.length > 0 && (
        <div className="shrink-0 px-3 pt-2 flex flex-wrap gap-1.5 bg-background border-t">
          {staged.map((s) => (
            <StagedThumb key={s.localId} attachment={s} onRemove={() => removeStaged(s.localId)} />
          ))}
        </div>
      )}
      <div className={cn('shrink-0 p-3 flex items-end gap-2 bg-background', staged.length === 0 && 'border-t')}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_ATTACHMENT_TYPES}
          className="hidden"
          onChange={(e) => {
            onFilesSelected(e.target.files)
            e.target.value = '' // allow picking the same file again later
          }}
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={streaming}
          className="shrink-0"
          aria-label={t('agents.chat.attachFile', 'Attach a photo or file')}
          title={t('agents.chat.attachFile', 'Attach a photo or file')}
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            // Auto-grow: reset then size to content. Capped via maxHeight.
            const el = e.target
            el.style.height = 'auto'
            el.style.height = `${Math.min(el.scrollHeight, 200)}px`
          }}
          rows={1}
          placeholder={t('agents.chat.placeholder', { name: agent.name })}
          // h-10 matches the default Button height so the input + send
          // button line up when empty. Auto-grow above lifts it as the
          // user types more lines.
          className="flex-1 h-10 max-h-[200px] rounded-md border bg-card px-3 py-2 text-sm resize-none leading-5 overflow-y-auto"
          onKeyDown={(e) => {
            // Enter sends; Shift+Enter inserts a newline. IME composition
            // (e.g. accented chars on Mac, CJK input) must not be hijacked.
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              send()
            }
          }}
        />
        {speech.supported && synth.supported && (
          <Button
            type="button"
            variant={voiceMode ? 'destructive' : 'outline'}
            onClick={toggleVoiceMode}
            className={cn('shrink-0', voiceMode && 'animate-pulse')}
            aria-label={voiceMode ? t('agents.chat.voiceModeStop', 'Turn off voice mode') : t('agents.chat.voiceModeStart', 'Turn on voice mode')}
            title={voiceMode ? t('agents.chat.voiceModeStop', 'Turn off voice mode') : t('agents.chat.voiceModeStart', 'Turn on voice mode — hands-free, good for driving')}
          >
            <Car className="h-4 w-4" />
          </Button>
        )}
        {speech.supported && (
          <Button
            type="button"
            variant={speech.listening ? 'destructive' : 'outline'}
            onClick={() => (speech.listening ? speech.stop() : speech.start())}
            disabled={streaming || voiceMode}
            className="shrink-0"
            aria-label={speech.listening ? t('agents.chat.voiceStop') : t('agents.chat.voiceStart')}
          >
            {speech.listening ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </Button>
        )}
        <Button
          onClick={() => send()}
          disabled={streaming || (!input.trim() && staged.filter((s) => s.id && !s.uploading).length === 0) || staged.some((s) => s.uploading)}
          className="shrink-0"
        >
          {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** One attachment chip, used both in the pre-send staging row and in the
 * optimistic "pendingUser" bubble. Images show their local blob: preview
 * (no server round trip needed pre-send); PDFs show a generic icon. */
function StagedThumb({ attachment, onRemove }: { attachment: StagedAttachment; onRemove?: () => void }) {
  const isImage = attachment.mime.startsWith('image/')
  return (
    <div
      className={cn(
        'relative group h-14 w-14 rounded-md border overflow-hidden flex items-center justify-center bg-muted shrink-0',
        attachment.error && 'border-rose-400',
      )}
      title={attachment.error ? `${attachment.filename}: ${attachment.error}` : `${attachment.filename} (${formatFileSize(attachment.size_bytes)})`}
    >
      {isImage && attachment.previewUrl ? (
        <img src={attachment.previewUrl} alt={attachment.filename} className="h-full w-full object-cover" />
      ) : (
        <FileText className="h-5 w-5 text-muted-foreground" />
      )}
      {attachment.uploading && (
        <div className="absolute inset-0 bg-background/60 flex items-center justify-center">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      )}
      {attachment.error && !attachment.uploading && (
        <div className="absolute inset-0 bg-rose-950/60 flex items-center justify-center">
          <AlertCircle className="h-4 w-4 text-rose-200" />
        </div>
      )}
      {onRemove && !attachment.uploading && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute top-0.5 right-0.5 h-4 w-4 rounded-full bg-background/90 border flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X className="h-2.5 w-2.5" />
        </button>
      )}
    </div>
  )
}

/** An attachment already on a persisted message — fetches its bytes
 * through the authenticated endpoint (images render inline; anything
 * else, currently just PDFs, shows a filename chip with a download
 * click-through). */
function HistoryAttachmentThumb({ agentId, attachment }: { agentId: string; attachment: ChatAttachmentMeta }) {
  const isImage = attachment.mime.startsWith('image/')
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!isImage) return
    let objectUrl: string | null = null
    let cancelled = false
    agents.attachments.fetchBlob(agentId, attachment.id).then((blob) => {
      if (cancelled) return
      objectUrl = URL.createObjectURL(blob)
      setUrl(objectUrl)
    }).catch(() => {})
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [agentId, attachment.id, isImage])

  const openFile = async () => {
    try {
      const blob = await agents.attachments.fetchBlob(agentId, attachment.id)
      const objectUrl = URL.createObjectURL(blob)
      window.open(objectUrl, '_blank')
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
    } catch {
      // best-effort — no toast plumbing in this component
    }
  }

  if (isImage) {
    return (
      <button type="button" onClick={openFile} className="h-20 w-20 rounded-md border overflow-hidden bg-muted/50 shrink-0">
        {url ? (
          <img src={url} alt={attachment.filename} className="h-full w-full object-cover" />
        ) : (
          <div className="h-full w-full flex items-center justify-center">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        )}
      </button>
    )
  }
  return (
    <button
      type="button"
      onClick={openFile}
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-md border bg-muted/50 text-xs max-w-[180px]"
      title={attachment.filename}
    >
      <FileIcon className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{attachment.filename}</span>
    </button>
  )
}

/**
 * Persisted history. Pairs each assistant tool_call with its matching
 * `tool` message (looked up by tool_call_id) so the call and its result
 * render together in a single expandable chip — same UX as the live
 * streaming draft.
 */
function HistoryView({ agent, history }: { agent: Agent; history: AgentMessage[] }) {
  const resultsById = useMemo(() => {
    const map: Record<string, AgentMessage> = {}
    for (const m of history) {
      if (m.role === 'tool') {
        const id = m.tool_result?.tool_call_id
        if (id) map[id] = m
      }
    }
    return map
  }, [history])

  return (
    <>
      {history
        .filter((m) => m.role !== 'tool') // tool messages render under their assistant call
        .map((m) => {
          if (m.role === 'user') {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[80%] rounded-lg px-3 py-2 bg-primary text-primary-foreground">
                  {!!m.attachments?.length && (
                    <div className="flex flex-wrap gap-1.5 mb-1.5">
                      {m.attachments.map((a) => (
                        <HistoryAttachmentThumb key={a.id} agentId={agent.id} attachment={a} />
                      ))}
                    </div>
                  )}
                  {m.content && <div className="whitespace-pre-wrap text-sm">{m.content}</div>}
                </div>
              </div>
            )
          }
          if (m.role === 'assistant') {
            return (
              <div key={m.id} className="space-y-2">
                {/* End users don't need to see raw tool-call traffic — only
                    proposals, which carry an Apply button. */}
                {m.tool_calls?.map((tc) => {
                  const tres = resultsById[tc.id]
                  const data = tres?.tool_result?.data
                  if (!isProposalToolName(tc.name) || !data || !isProposalData(data)) return null
                  // Persisted tool_call_id is stable across reloads —
                  // perfect localStorage key for the "applied" marker.
                  return <ProposalCard key={tc.id} toolCallId={tc.id} data={data as Record<string, unknown>} />
                })}
                {m.content && (
                  <div className="rounded-lg px-3 py-2 bg-muted">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1 flex items-center gap-1.5">
                      <Sparkles className="h-3 w-3" /> {agent.name}
                    </div>
                    <Markdown>{m.content}</Markdown>
                  </div>
                )}
              </div>
            )
          }
          return null
        })}
    </>
  )
}


/** Shown in a fresh conversation (no history, no draft). Centers the
 *  Securo mark + agent name and surfaces ~6 randomized example prompts
 *  pulled from i18n. Picking one fills the textarea and focuses it
 *  (cheaper than auto-sending — gives the user a chance to tweak). */
function ChatEmptyState({ agent, onPick }: { agent: Agent; onPick: (text: string) => void }) {
  const { t } = useTranslation()

  // Resolve the LLM connector tied to this agent so the empty state
  // can show "Connected via X" — useful trust signal: the user knows
  // which provider/key/model is going to handle the next message.
  // Falls back gracefully when the agent has no connection_id (uses
  // raw provider/model fields or instance default).
  const { data: connections } = useQuery({
    queryKey: ['agent-connections'],
    queryFn: () => agents.connections.list(),
    staleTime: 1000 * 60,
  })
  const connectorLabel = useMemo<string | null>(() => {
    if (agent.connection_id) {
      const conn = connections?.find((c) => c.id === agent.connection_id)
      if (conn) {
        const model = agent.model || conn.default_model
        return model ? `${conn.name} · ${model}` : conn.name
      }
    }
    if (agent.provider) {
      return agent.model ? `${agent.provider} · ${agent.model}` : agent.provider
    }
    return null
  }, [agent.connection_id, agent.provider, agent.model, connections])

  // Pull the localized prompt pool. Each locale ships ~10 short tips;
  // we shuffle and take the first 6 so reopening a fresh chat doesn't
  // always show the same chips.
  const allPrompts = useMemo<string[]>(() => {
    const raw = t('agents.emptyState.suggestions', { returnObjects: true })
    return Array.isArray(raw) ? (raw as string[]) : []
    // Re-randomize each time the agent changes so switching agents
    // refreshes the suggestion set too.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, agent.id])

  const picks = useMemo(() => {
    const pool = [...allPrompts]
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[pool[i], pool[j]] = [pool[j], pool[i]]
    }
    return pool.slice(0, 3)
  }, [allPrompts])

  return (
    <div className="flex flex-col items-center justify-center text-center gap-5 py-12 min-h-[65vh]">
      {/* Brand mark — uses the primary indigo so it reads as Securo, not
          as the agent's accent color. Transparent background. */}
      <ShellLogo size={56} className="text-primary opacity-90" />
      <div className="space-y-1 px-6">
        <div className="text-base font-semibold">{agent.name}</div>
        {agent.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">{agent.description}</p>
        )}
        {connectorLabel && (
          <div className="text-[11px] text-muted-foreground/80 mt-1.5">
            {t('agents.emptyState.connectedVia', 'via')} <span className="font-mono">{connectorLabel}</span>
          </div>
        )}
      </div>
      {picks.length > 0 && (
        <div className="w-full px-3 mt-1">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground/80 mb-2 text-center">
            {t('agents.emptyState.tryAsking', 'Try asking')}
          </div>
          <div className="flex flex-col gap-1.5">
            {picks.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onPick(p)}
                className="text-left text-sm px-3 py-2 rounded-md border border-border bg-background/40 hover:bg-muted transition-colors"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
