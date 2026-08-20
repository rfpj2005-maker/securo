/** Strips markdown (and embedded ```securo-chart data blocks) down to
 * something reasonable to pass to SpeechSynthesis — reading "asterisk
 * asterisk bold asterisk asterisk" or a raw chart JSON payload aloud would
 * be worse than useless while driving. */
export function toSpeechText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, ' ') // fenced code blocks (incl. securo-chart)
    .replace(/`([^`]+)`/g, '$1') // inline code
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1') // images -> alt text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links -> link text
    .replace(/^#{1,6}\s+/gm, '') // headers
    .replace(/^>\s?/gm, '') // blockquotes
    .replace(/^\s*[-*+]\s+/gm, '') // bullet lists
    .replace(/^\s*\d+\.\s+/gm, '') // numbered lists
    .replace(/^\s*[-*_]{3,}\s*$/gm, '') // horizontal rules
    .replace(/(\*\*\*|\*\*|\*|___|__|_|~~)/g, '') // emphasis/strikethrough markers
    .replace(/\n{2,}/g, '. ')
    .replace(/\n/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
