'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ThumbsUp, ThumbsDown, MessageSquare, X, Send, Check } from 'lucide-react';

interface FeedbackWidgetProps {
  pageId?: string;
  onFeedbackSubmit?: (feedback: FeedbackData) => void;
}

interface FeedbackData {
  type: 'positive' | 'negative' | 'comment';
  message?: string;
  pageId?: string;
  timestamp: string;
}

export function FeedbackWidget({ pageId, onFeedbackSubmit }: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'positive' | 'negative' | 'comment' | null>(null);
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleInitialFeedback = (type: 'positive' | 'negative') => {
    setFeedbackType(type);
    setIsOpen(true);

    // Submit simple feedback immediately
    if (type === 'positive') {
      submitFeedback(type, '');
    }
  };

  const handleCommentClick = () => {
    setFeedbackType('comment');
    setIsOpen(true);
  };

  const submitFeedback = async (type: FeedbackData['type'], feedbackMessage: string) => {
    setIsSubmitting(true);

    const feedbackData: FeedbackData = {
      type,
      message: feedbackMessage,
      pageId,
      timestamp: new Date().toISOString()
    };

    try {
      // Call the callback if provided
      if (onFeedbackSubmit) {
        onFeedbackSubmit(feedbackData);
      } else {
        // Default: Send to API
        await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(feedbackData)
        });
      }

      setIsSubmitted(true);
      setTimeout(() => {
        setIsOpen(false);
        setIsSubmitted(false);
        setFeedbackType(null);
        setMessage('');
      }, 2000);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = () => {
    if (feedbackType && (feedbackType === 'positive' || message.trim())) {
      submitFeedback(feedbackType, message);
    }
  };

  return (
    <>
      {/* Floating feedback buttons */}
      <div className="fixed bottom-6 right-6 z-40 flex flex-col gap-2">
        {!isOpen && (
          <>
            <div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 rounded-lg shadow-lg border p-2 flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInitialFeedback('positive')}
                className="hover:bg-green-100 dark:hover:bg-green-900/20"
                title="This page was helpful"
              >
                <ThumbsUp className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleInitialFeedback('negative')}
                className="hover:bg-red-100 dark:hover:bg-red-900/20"
                title="This page needs improvement"
              >
                <ThumbsDown className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCommentClick}
                className="hover:bg-blue-100 dark:hover:bg-blue-900/20"
                title="Leave a comment"
              >
                <MessageSquare className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground text-center">Was this helpful?</p>
          </>
        )}
      </div>

      {/* Feedback form modal */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-80 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 rounded-lg shadow-xl border">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">
                {isSubmitted
                  ? 'Thank you!'
                  : feedbackType === 'positive'
                  ? 'Glad this helped!'
                  : feedbackType === 'negative'
                  ? 'How can we improve?'
                  : 'Leave a comment'}
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsOpen(false)}
                className="h-6 w-6 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {isSubmitted ? (
              <div className="flex flex-col items-center py-4">
                <Check className="h-12 w-12 text-green-500 mb-2" />
                <p className="text-sm text-muted-foreground">Your feedback has been received</p>
              </div>
            ) : (
              <>
                {(feedbackType === 'negative' || feedbackType === 'comment') && (
                  <>
                    <Textarea
                      placeholder={
                        feedbackType === 'negative'
                          ? 'Tell us what could be better...'
                          : 'Share your thoughts...'
                      }
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      className="min-h-[100px] mb-3"
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsOpen(false)}
                        className="flex-1"
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSubmit}
                        disabled={!message.trim() || isSubmitting}
                        className="flex-1 flex items-center gap-2"
                      >
                        <Send className="h-3 w-3" />
                        {isSubmitting ? 'Sending...' : 'Send'}
                      </Button>
                    </div>
                  </>
                )}

                {feedbackType === 'positive' && !isSubmitted && (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Want to tell us more?
                    </p>
                    <Textarea
                      placeholder="Optional: Share what you found helpful..."
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      className="min-h-[80px]"
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsOpen(false)}
                        className="flex-1"
                      >
                        Close
                      </Button>
                      {message.trim() && (
                        <Button
                          size="sm"
                          onClick={handleSubmit}
                          disabled={isSubmitting}
                          className="flex-1 flex items-center gap-2"
                        >
                          <Send className="h-3 w-3" />
                          {isSubmitting ? 'Sending...' : 'Send'}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// Simple inline feedback for end of articles
export function InlineFeedback({ pageId, className = '' }: { pageId?: string; className?: string }) {
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleFeedback = async (type: 'positive' | 'negative') => {
    setFeedback(type);

    const feedbackData: FeedbackData = {
      type,
      pageId,
      timestamp: new Date().toISOString()
    };

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData)
      });
      setIsSubmitted(true);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  if (isSubmitted) {
    return (
      <div className={`flex items-center justify-center gap-2 py-4 ${className}`}>
        <Check className="h-5 w-5 text-green-500" />
        <span className="text-sm text-muted-foreground">Thanks for your feedback!</span>
      </div>
    );
  }

  return (
    <div className={`border-t pt-8 ${className}`}>
      <div className="flex flex-col items-center gap-4">
        <p className="text-sm font-medium">Was this page helpful?</p>
        <div className="flex gap-2">
          <Button
            variant={feedback === 'positive' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFeedback('positive')}
            className="flex items-center gap-2"
          >
            <ThumbsUp className="h-4 w-4" />
            Yes
          </Button>
          <Button
            variant={feedback === 'negative' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFeedback('negative')}
            className="flex items-center gap-2"
          >
            <ThumbsDown className="h-4 w-4" />
            No
          </Button>
        </div>
      </div>
    </div>
  );
}