'use client';

import { useState } from 'react';
import Link from 'next/link';
import { submitSupportForm } from '@/lib/api';
import type { SupportFormData, SupportFormResponse } from '@/lib/types';

type FormState = 'idle' | 'submitting' | 'success' | 'error';

const CATEGORIES = [
  { value: 'general', label: 'General Question' },
  { value: 'technical', label: 'Technical Issue' },
  { value: 'billing', label: 'Billing & Subscription' },
  { value: 'bug_report', label: 'Bug Report' },
  { value: 'feedback', label: 'Feedback & Suggestion' },
];

const PRIORITIES = [
  { value: 'low', label: 'Low — Non-urgent question' },
  { value: 'medium', label: 'Medium — Affecting my work' },
  { value: 'high', label: 'High — Blocking my team' },
];

export default function SupportForm() {
  const [formState, setFormState] = useState<FormState>('idle');
  const [result, setResult] = useState<SupportFormResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [charCount, setCharCount] = useState(0);

  const [form, setForm] = useState<SupportFormData>({
    name: '',
    email: '',
    subject: '',
    category: 'general',
    priority: 'medium',
    message: '',
  });

  const [errors, setErrors] = useState<Partial<SupportFormData>>({});

  function validate(): boolean {
    const newErrors: Partial<SupportFormData> = {};

    if (!form.name || form.name.trim().length < 2)
      newErrors.name = 'Name must be at least 2 characters';
    if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      newErrors.email = 'Please enter a valid email address';
    if (!form.subject || form.subject.trim().length < 5)
      newErrors.subject = 'Subject must be at least 5 characters';
    if (!form.message || form.message.trim().length < 10)
      newErrors.message = 'Message must be at least 10 characters';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setFormState('submitting');
    setError('');

    try {
      const response = await submitSupportForm(form);
      setResult(response);
      setFormState('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      setFormState('error');
    }
  }

  async function copyTicketId() {
    if (result?.ticket_id) {
      await navigator.clipboard.writeText(result.ticket_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (name === 'message') setCharCount(value.length);
    if (errors[name as keyof SupportFormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  // SUCCESS STATE
  if (formState === 'success' && result) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-8 animate-fade-in">
        {/* Success animation */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
            <svg
              className="w-10 h-10 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>

        <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
          Request Submitted!
        </h2>
        <p className="text-gray-500 text-center mb-6">
          Our AI support agent is processing your request.
        </p>

        {/* Ticket ID */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-4">
          <p className="text-xs text-gray-500 mb-1">Your Ticket ID</p>
          <div className="flex items-center justify-between">
            <code className="text-sm font-mono text-gray-800 break-all">
              {result.ticket_id}
            </code>
            <button
              onClick={copyTicketId}
              className="ml-3 flex-shrink-0 text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {copied ? '✓ Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⏱️</span>
            <div>
              <p className="text-sm font-medium text-gray-800">Expected Response</p>
              <p className="text-sm text-gray-600">{result.estimated_response}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href={`/ticket/${result.ticket_id}`}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-xl text-center transition-colors"
          >
            Check Ticket Status
          </Link>
          <button
            onClick={() => {
              setFormState('idle');
              setResult(null);
              setForm({
                name: '',
                email: '',
                subject: '',
                category: 'general',
                priority: 'medium',
                message: '',
              });
            }}
            className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 px-4 rounded-xl text-center transition-colors"
          >
            Submit Another
          </button>
        </div>

        {result.mode === 'DEMO' && (
          <p className="text-xs text-center text-yellow-600 mt-4">
            🟡 Running in DEMO mode — AI is processing your request
          </p>
        )}
      </div>
    );
  }

  // FORM STATE
  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-2xl border border-gray-200 p-6 sm:p-8"
    >
      <div className="space-y-5">
        {/* Name + Email row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Your Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Ahmed Khan"
              className={`w-full border rounded-xl px-4 py-2.5 text-sm outline-none transition-colors ${
                errors.name
                  ? 'border-red-300 focus:border-red-500 bg-red-50'
                  : 'border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-200'
              }`}
            />
            {errors.name && (
              <p className="text-xs text-red-500 mt-1">{errors.name}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Email Address <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="ahmed@example.com"
              className={`w-full border rounded-xl px-4 py-2.5 text-sm outline-none transition-colors ${
                errors.email
                  ? 'border-red-300 focus:border-red-500 bg-red-50'
                  : 'border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-200'
              }`}
            />
            {errors.email && (
              <p className="text-xs text-red-500 mt-1">{errors.email}</p>
            )}
          </div>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Subject <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="subject"
            value={form.subject}
            onChange={handleChange}
            placeholder="e.g., Cannot reset my password"
            className={`w-full border rounded-xl px-4 py-2.5 text-sm outline-none transition-colors ${
              errors.subject
                ? 'border-red-300 focus:border-red-500 bg-red-50'
                : 'border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-200'
            }`}
          />
          {errors.subject && (
            <p className="text-xs text-red-500 mt-1">{errors.subject}</p>
          )}
        </div>

        {/* Category + Priority row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Category
            </label>
            <select
              name="category"
              value={form.category}
              onChange={handleChange}
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-200 bg-white transition-colors"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Priority
            </label>
            <select
              name="priority"
              value={form.priority}
              onChange={handleChange}
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-200 bg-white transition-colors"
            >
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Message */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Message <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <textarea
              name="message"
              value={form.message}
              onChange={handleChange}
              rows={5}
              placeholder="Please describe your issue in detail. The more context you provide, the better our AI can assist you."
              className={`w-full border rounded-xl px-4 py-3 text-sm outline-none transition-colors resize-none ${
                errors.message
                  ? 'border-red-300 focus:border-red-500 bg-red-50'
                  : 'border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-200'
              }`}
            />
            <span className="absolute bottom-3 right-3 text-xs text-gray-400">
              {charCount}/5000
            </span>
          </div>
          {errors.message && (
            <p className="text-xs text-red-500 mt-1">{errors.message}</p>
          )}
        </div>

        {/* Error Message */}
        {formState === 'error' && error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={formState === 'submitting'}
          className={`w-full py-3 px-6 rounded-xl font-semibold text-sm transition-all ${
            formState === 'submitting'
              ? 'bg-blue-400 text-white cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-md'
          }`}
        >
          {formState === 'submitting' ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Submitting...
            </span>
          ) : (
            'Submit Support Request'
          )}
        </button>

        <p className="text-xs text-center text-gray-400">
          By submitting, you agree to our support terms. AI responds 24/7 in seconds.
        </p>
      </div>
    </form>
  );
}
