'use client';

import { useState, useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';

// Import additional language support
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-yaml';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  highlightLines?: number[];
  className?: string;
}

const languageLabels: Record<string, string> = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  jsx: 'React JSX',
  tsx: 'React TSX',
  python: 'Python',
  go: 'Go',
  bash: 'Bash',
  shell: 'Shell',
  json: 'JSON',
  yaml: 'YAML',
  css: 'CSS',
};

export function CodeBlock({
  code,
  language = 'javascript',
  filename,
  showLineNumbers = false,
  highlightLines = [],
  className,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [highlightedCode, setHighlightedCode] = useState('');

  useEffect(() => {
    const highlighted = Prism.highlight(
      code,
      Prism.languages[language] || Prism.languages.javascript,
      language
    );
    setHighlightedCode(highlighted);
  }, [code, language]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = highlightedCode.split('\n');

  return (
    <div className={cn('group relative rounded-lg bg-gray-900 text-gray-100', className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <div className="flex items-center space-x-2">
          {filename && (
            <span className="text-sm text-gray-400">{filename}</span>
          )}
          <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
            {languageLabels[language] || language}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 rounded-md px-2 py-1 text-sm text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-100"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 text-green-400" />
              <span className="text-green-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <div className="overflow-x-auto">
        <pre className="p-4">
          <code className={`language-${language}`}>
            {lines.map((line, index) => (
              <div
                key={index}
                className={cn(
                  'table-row',
                  highlightLines.includes(index + 1) && 'bg-gray-800/50'
                )}
              >
                {showLineNumbers && (
                  <span className="table-cell select-none pr-4 text-right text-gray-500">
                    {index + 1}
                  </span>
                )}
                <span
                  className="table-cell"
                  dangerouslySetInnerHTML={{ __html: line || ' ' }}
                />
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}

// Multi-language tabbed code block
interface TabbedCodeBlockProps {
  examples: {
    language: string;
    code: string;
    filename?: string;
  }[];
  defaultLanguage?: string;
  className?: string;
}

export function TabbedCodeBlock({
  examples,
  defaultLanguage,
  className,
}: TabbedCodeBlockProps) {
  const [activeLanguage, setActiveLanguage] = useState(
    defaultLanguage || examples[0]?.language || 'javascript'
  );

  const activeExample = examples.find(ex => ex.language === activeLanguage) || examples[0];

  return (
    <div className={cn('rounded-lg border border-gray-200 dark:border-gray-800', className)}>
      {/* Language tabs */}
      <div className="flex border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
        {examples.map((example) => (
          <button
            key={example.language}
            onClick={() => setActiveLanguage(example.language)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors',
              activeLanguage === example.language
                ? 'border-b-2 border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
            )}
          >
            {languageLabels[example.language] || example.language}
          </button>
        ))}
      </div>

      {/* Active code block */}
      {activeExample && (
        <CodeBlock
          code={activeExample.code}
          language={activeExample.language}
          filename={activeExample.filename}
        />
      )}
    </div>
  );
}