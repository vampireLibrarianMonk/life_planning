import React from 'react'

function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*')) return <em key={i}>{part.slice(1, -1)}</em>
    return part
  })
}

export default function MiniMarkdown({ text, maxHeight = 150 }) {
  if (!text) return null
  const lines = text.split('\n')
  const elements = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (line.trim() === '') { i++; continue }
    if (/^\*?\*?\d+\.?\*?\*?\s/.test(line)) {
      const items = []
      while (i < lines.length && /^\*?\*?\d+\.?\*?\*?\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\*?\*?\d+\.?\*?\*?\s*/, ''))
        i++
      }
      elements.push(<ol key={elements.length} style={{ margin: '4px 0', paddingLeft: 20, fontSize: 12 }}>{items.map((item, j) => <li key={j} style={{ marginBottom: 2 }}>{renderInline(item)}</li>)}</ol>)
      continue
    }
    if (line.startsWith('• ') || line.startsWith('- ')) {
      const items = []
      while (i < lines.length && (lines[i].startsWith('• ') || lines[i].startsWith('- '))) {
        items.push(lines[i].slice(2))
        i++
      }
      elements.push(<ul key={elements.length} style={{ margin: '4px 0', paddingLeft: 20, fontSize: 12, listStyleType: 'disc' }}>{items.map((item, j) => <li key={j} style={{ marginBottom: 2 }}>{renderInline(item)}</li>)}</ul>)
      continue
    }
    elements.push(<p key={elements.length} style={{ margin: '4px 0', fontSize: 12 }}>{renderInline(line)}</p>)
    i++
  }
  return <div style={{ maxHeight, overflowY: 'auto', color: '#555', lineHeight: 1.6, marginTop: 4 }}>{elements}</div>
}
