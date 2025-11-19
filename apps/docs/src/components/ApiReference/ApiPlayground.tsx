'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { CodeBlock } from '../CodeBlock/CodeBlock';
import { ChevronDown, ChevronRight, Play, Copy, Check } from 'lucide-react';

interface ApiPlaygroundProps {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  baseUrl?: string;
  defaultEnvironment?: 'test' | 'live';
  headers?: Record<string, string>;
  parameters?: {
    path?: Array<{
      name: string;
      type: string;
      required?: boolean;
      description?: string;
      example?: string;
    }>;
    query?: Array<{
      name: string;
      type: string;
      required?: boolean;
      description?: string;
      example?: string;
    }>;
    body?: Array<{
      name: string;
      type: string;
      required?: boolean;
      description?: string;
      example?: any;
    }>;
  };
}

export function ApiPlayground({
  method,
  path,
  baseUrl: _baseUrl = 'https://api.plinto.dev',
  defaultEnvironment = 'test',
  headers = {},
  parameters
}: ApiPlaygroundProps) {
  const [environment, setEnvironment] = useState(defaultEnvironment);
  const [isExpanded, setIsExpanded] = useState(false);
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});
  const [bodyContent, setBodyContent] = useState('');
  const [customHeaders, setCustomHeaders] = useState<Record<string, string>>(headers);
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const environments = {
    test: 'https://api-test.plinto.dev',
    live: 'https://api.plinto.dev'
  };

  const buildUrl = () => {
    let url = path;

    // Replace path parameters
    Object.entries(pathParams).forEach(([key, value]) => {
      url = url.replace(`{${key}}`, value);
    });

    // Add query parameters
    const queryString = Object.entries(queryParams)
      .filter(([_, value]) => value)
      .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
      .join('&');

    if (queryString) {
      url += `?${queryString}`;
    }

    return `${environments[environment]}${url}`;
  };

  const executeRequest = async () => {
    setLoading(true);
    setResponse(null);

    try {
      const url = buildUrl();
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...customHeaders
        }
      };

      if (['POST', 'PUT', 'PATCH'].includes(method) && bodyContent) {
        options.body = bodyContent;
      }

      const startTime = Date.now();
      const res = await fetch(url, options);
      const duration = Date.now() - startTime;

      const responseData = await res.json().catch(() => res.text());

      setResponse({
        status: res.status,
        statusText: res.statusText,
        headers: Object.fromEntries(res.headers.entries()),
        data: responseData,
        duration
      });
    } catch (error) {
      setResponse({
        error: error instanceof Error ? error.message : 'Request failed',
        status: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const copyAsCurl = () => {
    const url = buildUrl();
    let curlCommand = `curl -X ${method} "${url}"`;

    Object.entries(customHeaders).forEach(([key, value]) => {
      curlCommand += ` \\\n  -H "${key}: ${value}"`;
    });

    if (['POST', 'PUT', 'PATCH'].includes(method) && bodyContent) {
      curlCommand += ` \\\n  -d '${bodyContent}'`;
    }

    navigator.clipboard.writeText(curlCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border rounded-lg bg-muted/20">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/40 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <span className="font-medium">Try It</span>
        </div>
        <div className="flex items-center gap-2">
          <Select value={environment} onValueChange={(value: 'test' | 'live') => setEnvironment(value)}>
            <SelectTrigger className="w-32 h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="test">Test</SelectItem>
              <SelectItem value="live">Live</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </button>

      {isExpanded && (
        <div className="p-4 border-t space-y-4">
          {/* Path Parameters */}
          {parameters?.path && parameters.path.length > 0 && (
            <div className="space-y-2">
              <Label>Path Parameters</Label>
              {parameters.path.map((param) => (
                <div key={param.name} className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      placeholder={param.name}
                      value={pathParams[param.name] || ''}
                      onChange={(e) => setPathParams(prev => ({ ...prev, [param.name]: e.target.value }))}
                    />
                    {param.description && (
                      <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Query Parameters */}
          {parameters?.query && parameters.query.length > 0 && (
            <div className="space-y-2">
              <Label>Query Parameters</Label>
              {parameters.query.map((param) => (
                <div key={param.name} className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      placeholder={param.name}
                      value={queryParams[param.name] || ''}
                      onChange={(e) => setQueryParams(prev => ({ ...prev, [param.name]: e.target.value }))}
                    />
                    {param.description && (
                      <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Request Headers */}
          <div className="space-y-2">
            <Label>Headers</Label>
            <div className="space-y-2">
              {Object.entries(customHeaders).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <Input placeholder="Header name" value={key} className="flex-1" readOnly />
                  <Input
                    placeholder="Header value"
                    value={value}
                    className="flex-1"
                    onChange={(e) => setCustomHeaders(prev => ({ ...prev, [key]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Request Body */}
          {['POST', 'PUT', 'PATCH'].includes(method) && (
            <div className="space-y-2">
              <Label>Request Body</Label>
              <Textarea
                placeholder="Enter JSON body"
                value={bodyContent}
                onChange={(e) => setBodyContent(e.target.value)}
                className="font-mono text-sm min-h-[120px]"
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button onClick={executeRequest} disabled={loading} className="flex items-center gap-2">
              <Play className="h-4 w-4" />
              {loading ? 'Sending...' : 'Send Request'}
            </Button>
            <Button variant="outline" onClick={copyAsCurl} className="flex items-center gap-2">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy as cURL'}
            </Button>
          </div>

          {/* Response */}
          {response && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Response</Label>
                {response.duration && (
                  <span className="text-xs text-muted-foreground">{response.duration}ms</span>
                )}
              </div>

              {response.error ? (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                  <p className="text-sm text-destructive">{response.error}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                      response.status >= 200 && response.status < 300
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                        : response.status >= 400
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                    }`}>
                      {response.status} {response.statusText}
                    </span>
                  </div>

                  {response.data && (
                    <CodeBlock
                      code={typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 2)}
                      language="json"
                      showLineNumbers={false}
                    />
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}