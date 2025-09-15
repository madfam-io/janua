'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface TOCItem {
  id: string;
  text: string;
  level: number;
}

export function TableOfContents() {
  const [headings, setHeadings] = useState<TOCItem[]>([]);
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    // Get all headings from the article
    const article = document.querySelector('article');
    if (!article) return;

    const headingElements = article.querySelectorAll('h2, h3, h4');
    const items: TOCItem[] = Array.from(headingElements).map((heading) => {
      const id = heading.id || heading.textContent?.toLowerCase().replace(/\s+/g, '-') || '';
      
      // Ensure heading has an ID for linking
      if (!heading.id) {
        heading.id = id;
      }

      return {
        id,
        text: heading.textContent || '',
        level: parseInt(heading.tagName[1]),
      };
    });

    setHeadings(items);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      {
        rootMargin: '-100px 0px -70% 0px',
      }
    );

    headings.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (element) {
        observer.observe(element);
      }
    });

    return () => {
      headings.forEach(({ id }) => {
        const element = document.getElementById(id);
        if (element) {
          observer.unobserve(element);
        }
      });
    };
  }, [headings]);

  if (headings.length === 0) {
    return null;
  }

  return (
    <div>
      <h5 className="mb-4 text-sm font-semibold text-gray-900 dark:text-gray-100">
        On this page
      </h5>
      <nav className="space-y-1">
        {headings.map((heading) => (
          <a
            key={heading.id}
            href={`#${heading.id}`}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(heading.id)?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
              });
            }}
            className={cn(
              'block text-sm transition-colors',
              heading.level === 2 && 'font-medium',
              heading.level === 3 && 'ml-4',
              heading.level === 4 && 'ml-8',
              activeId === heading.id
                ? 'text-indigo-600 dark:text-indigo-400'
                : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
            )}
          >
            {heading.text}
          </a>
        ))}
      </nav>
    </div>
  );
}