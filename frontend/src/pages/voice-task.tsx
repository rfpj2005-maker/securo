import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { tasks as tasksApi } from '@/lib/api'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Mic, Square, ArrowLeft, Check } from 'lucide-react'
import { useSpeechRecognition } from '@/hooks/use-speech-recognition'

const DEFAULT_CATEGORIES = ['marketing', 'management', 'commercial', 'administrative']

// Naive keyword match so saying "marketing, cotar placa..." pre-selects the
// category — purely a convenience default, always editable before saving.
function guessCategory(text: string): string {
  const lower = text.toLowerCase()
  if (lower.includes('marketing')) return 'marketing'
  if (lower.includes('gestão') || lower.includes('gestao') || lower.includes('management')) return 'management'
  if (lower.includes('comercial')) return 'commercial'
  return 'administrative'
}

export default function VoiceTaskPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { supported, listening, transcript, setTranscript, start, stop, resetTranscript } = useSpeechRecognition('pt-BR')
  const [category, setCategory] = useState('administrative')

  const knownLabels: Record<string, string> = {
    marketing: t('tasks.categoryMarketing'),
    management: t('tasks.categoryManagement'),
    commercial: t('tasks.categoryCommercial'),
    administrative: t('tasks.categoryAdministrative'),
    meetings: t('tasks.categoryMeetings'),
  }
  const categoryLabel = (c: string) => knownLabels[c] ?? c

  const { data: allTasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => tasksApi.list(),
  })
  const availableCategories = useMemo(() => {
    const set = new Set(DEFAULT_CATEGORIES)
    for (const task of allTasks ?? []) set.add(task.category)
    return Array.from(set)
  }, [allTasks])

  useEffect(() => {
    // Re-guess the category as the live transcript comes in; the field
    // stays a normal controlled input the user can override afterward.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (transcript) setCategory(guessCategory(transcript))
  }, [transcript])

  const createMutation = useMutation({
    mutationFn: (data: { title: string; category: string }) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success(t('tasks.created'))
      resetTranscript()
      setCategory('administrative')
    },
    onError: () => toast.error(t('common.error')),
  })

  return (
    <div className="min-h-screen flex flex-col items-center px-6 py-10 max-w-md mx-auto">
      <div className="w-full flex items-center gap-2 mb-8">
        <Button variant="ghost" size="icon" onClick={() => navigate('/tasks')}>
          <ArrowLeft size={18} />
        </Button>
        <h1 className="text-lg font-semibold text-foreground">{t('tasks.voiceTitle')}</h1>
      </div>

      {!supported ? (
        <p className="text-center text-muted-foreground text-sm mt-10">{t('tasks.voiceUnsupported')}</p>
      ) : (
        <>
          <button
            onClick={listening ? stop : start}
            className={`flex items-center justify-center rounded-full h-28 w-28 transition-all shrink-0 ${
              listening
                ? 'bg-destructive text-white animate-pulse shadow-lg shadow-destructive/30'
                : 'bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:bg-primary/90'
            }`}
            aria-label={listening ? t('tasks.voiceStop') : t('tasks.voiceStart')}
          >
            {listening ? <Square size={32} /> : <Mic size={36} />}
          </button>

          <p className="text-sm text-muted-foreground mt-4 text-center">
            {listening ? t('tasks.voiceListening') : t('tasks.voiceTapToStart')}
          </p>

          {transcript && (
            <div className="w-full mt-8 space-y-4">
              <div className="space-y-2">
                <Label>{t('tasks.taskTitle')}</Label>
                <textarea
                  className="w-full border border-border rounded-md px-3 py-2 text-sm bg-card resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                  rows={3}
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>{t('tasks.category')}</Label>
                <Input
                  list="voice-task-categories"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder={t('tasks.categoryPlaceholder')}
                />
                <datalist id="voice-task-categories">
                  {availableCategories.map((c) => (
                    <option key={c} value={c}>{categoryLabel(c)}</option>
                  ))}
                </datalist>
              </div>
              <Button
                className="w-full"
                size="lg"
                disabled={!transcript.trim() || createMutation.isPending}
                onClick={() => createMutation.mutate({ title: transcript.trim(), category: category.trim() || 'administrative' })}
              >
                <Check size={16} className="mr-1" />
                {t('tasks.voiceSave')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
