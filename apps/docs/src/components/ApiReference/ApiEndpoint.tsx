'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Play, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CodeBlock, TabbedCodeBlock } from '../CodeBlock/CodeBlock';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface Parameter {
  name: string;
  type: string;
  required?: boolean;
  description: string;
  default?: string;
  example?: string;
  children?: Parameter[];
}

interface Response {
  status: number;
  description: string;
  example: object | string;
}

interface ApiEndpointProps {
  method: HttpMethod;
  path: string;
  title: string;
  description: string;
  authenticated?: boolean;
  parameters?: {
    path?: Parameter[];
    query?: Parameter[];
    body?: Parameter[];
    headers?: Parameter[];
  };
  responses?: Response[];
  examples?: {
    language: string;
    code: string;
  }[];
  tryItEnabled?: boolean;
  baseUrl?: string;
}

const methodColors: Record<HttpMethod, string> = {
  GET: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  PUT: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  PATCH: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  DELETE: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

function ParameterRow({ param, depth = 0 }: { param: Parameter; depth?: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = param.children && param.children.length > 0;

  return (
    <>
      <tr className={cn('border-b border-gray-200 dark:border-gray-700', depth > 0 && 'bg-gray-50 dark:bg-gray-900')}>
        <td className="px-4 py-3">
          <div className="flex items-center" style={{ paddingLeft: `${depth * 20}px` }}>
            {hasChildren && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="mr-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
            )}
            <code className="text-sm font-mono text-indigo-600 dark:text-indigo-400">
              {param.name}
            </code>
            {param.required && (
              <span className="ml-2 text-xs text-red-600 dark:text-red-400">required</span>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <code className="text-xs text-gray-600 dark:text-gray-400">{param.type}</code>
        </td>
        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
          {param.description}
          {param.default && (
            <div className="mt-1 text-xs text-gray-500">
              Default: <code className="rounded bg-gray-100 px-1 py-0.5 dark:bg-gray-800">{param.default}</code>
            </div>
          )}
          {param.example && (
            <div className="mt-1 text-xs text-gray-500">
              Example: <code className="rounded bg-gray-100 px-1 py-0.5 dark:bg-gray-800">{param.example}</code>
            </div>
          )}
        </td>
      </tr>
      {expanded && hasChildren && param.children?.map((child, index) => (
        <ParameterRow key={`${child.name}-${index}`} param={child} depth={depth + 1} />
      ))}
    </>
  );
}

export function ApiEndpoint({
  method,
  path,
  title,
  description,
  authenticated = false,
  parameters,
  responses = [],
  examples = [],
  tryItEnabled = true,
  baseUrl = 'https://plinto.dev/api/v1',
}: ApiEndpointProps) {
  const [selectedResponseTab, setSelectedResponseTab] = useState(0);
  const [tryItOpen, setTryItOpen] = useState(false);
  const [environment, setEnvironment] = useState<'test' | 'live'>('test');
  const [apiKey, setApiKey] = useState('');
  const [requestBody, setRequestBody] = useState('');
  const [queryParams, _setQueryParams] = useState<Record<string, string>>({});
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [response, setResponse] = useState<any>(null);

  const handleTryIt = async () => {
    setExecuting(true);
    setResponse(null);

    // Build URL with path and query parameters
    let url = `${baseUrl}${path}`;
    
    // Replace path parameters
    Object.entries(pathParams).forEach(([key, value]) => {
      url = url.replace(`:${key}`, value);
    });

    // Add query parameters
    const queryString = new URLSearchParams(queryParams).toString();
    if (queryString) {
      url += `?${queryString}`;
    }

    // Build headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (authenticated && apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }

    if (environment === 'test') {
      headers['X-Environment'] = 'test';
    }

    try {
      const options: RequestInit = {
        method,
        headers,
      };

      if (method !== 'GET' && requestBody) {
        options.body = requestBody;
      }

      const res = await fetch(url, options);
      const data = await res.json();
      
      setResponse({
        status: res.status,
        statusText: res.statusText,
        headers: Object.fromEntries(res.headers.entries()),
        data,
      });
    } catch (error) {
      setResponse({
        error: error instanceof Error ? error.message : 'Request failed',
      });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="my-8 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="bg-gray-50 p-4 dark:bg-gray-900">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3">
              <span className={cn('rounded-md px-2 py-1 text-xs font-semibold uppercase', methodColors[method])}>
                {method}
              </span>
              <code className="text-sm font-mono text-gray-700 dark:text-gray-300">{path}</code>
              {authenticated && (
                <span className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                  <Lock className="mr-1 h-3 w-3" />
                  Authenticated
                </span>
              )}
            </div>
            <h3 className="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</p>
          </div>
          {tryItEnabled && (
            <button
              onClick={() => setTryItOpen(!tryItOpen)}
              className="ml-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              <Play className="mr-1 inline-block h-4 w-4" />
              Try it
            </button>
          )}
        </div>
      </div>

      {/* Try It Panel */}
      {tryItOpen && (
        <div className="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="space-y-4">
            {/* Environment Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Environment
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as 'test' | 'live')}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              >
                <option value="test">Test</option>
                <option value="live">Live</option>
              </select>
            </div>

            {/* API Key */}
            {authenticated && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  API Key
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key"
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                />
              </div>
            )}

            {/* Path Parameters */}
            {parameters?.path && parameters.path.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Path Parameters</h4>
                <div className="mt-2 space-y-2">
                  {parameters.path.map((param) => (
                    <div key={param.name}>
                      <label className="block text-xs text-gray-600 dark:text-gray-400">
                        {param.name} {param.required && <span className="text-red-500">*</span>}
                      </label>
                      <input
                        type="text"
                        value={pathParams[param.name] || ''}
                        onChange={(e) => setPathParams({ ...pathParams, [param.name]: e.target.value })}
                        placeholder={param.example || param.default || ''}
                        className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-1 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Request Body */}
            {method !== 'GET' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Request Body
                </label>
                <textarea
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  placeholder="{\n  \n}"
                  rows={6}
                  className="mt-1 block w-full rounded-md border border-gray-300 bg-gray-900 px-3 py-2 font-mono text-sm text-gray-100 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            )}

            {/* Execute Button */}
            <button
              onClick={handleTryIt}
              disabled={executing}
              className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              {executing ? 'Executing...' : 'Send Request'}
            </button>

            {/* Response */}
            {response && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Response</h4>
                <div className="mt-2">
                  {response.error ? (
                    <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-300">
                      Error: {response.error}
                    </div>
                  ) : (
                    <CodeBlock
                      code={JSON.stringify(response.data, null, 2)}
                      language="json"
                      filename={`${response.status} ${response.statusText}`}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Parameters */}
      {parameters && (Object.keys(parameters).length > 0) && (
        <div className="border-t border-gray-200 p-4 dark:border-gray-700">
          <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Parameters</h4>
          
          {parameters.path && parameters.path.length > 0 && (
            <div className="mb-4">
              <h5 className="mb-2 text-xs font-medium uppercase text-gray-600 dark:text-gray-400">Path Parameters</h5>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Name</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Type</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parameters.path.map((param) => (
                      <ParameterRow key={param.name} param={param} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {parameters.body && parameters.body.length > 0 && (
            <div className="mb-4">
              <h5 className="mb-2 text-xs font-medium uppercase text-gray-600 dark:text-gray-400">Body Parameters</h5>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Name</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Type</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parameters.body.map((param) => (
                      <ParameterRow key={param.name} param={param} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Code Examples */}
      {examples.length > 0 && (
        <div className="border-t border-gray-200 p-4 dark:border-gray-700">
          <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Example Request</h4>
          <TabbedCodeBlock examples={examples} />
        </div>
      )}

      {/* Responses */}
      {responses.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          <div className="flex border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
            {responses.map((res, index) => (
              <button
                key={index}
                onClick={() => setSelectedResponseTab(index)}
                className={cn(
                  'px-4 py-2 text-sm font-medium transition-colors',
                  selectedResponseTab === index
                    ? 'border-b-2 border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                    : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100'
                )}
              >
                <span className={cn(
                  'mr-1 inline-block h-2 w-2 rounded-full',
                  res.status >= 200 && res.status < 300 && 'bg-green-500',
                  res.status >= 400 && res.status < 500 && 'bg-orange-500',
                  res.status >= 500 && 'bg-red-500'
                )} />
                {res.status} {res.description}
              </button>
            ))}
          </div>
          <div className="p-4">
            <CodeBlock
              code={JSON.stringify(responses[selectedResponseTab].example, null, 2)}
              language="json"
            />
          </div>
        </div>
      )}
    </div>
  );
}