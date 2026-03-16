import SupportForm from '@/components/SupportForm';
import Link from 'next/link';

export default function SupportPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xs">T</span>
            </div>
            <span className="font-semibold text-gray-900">TechCorp Support</span>
          </Link>
          <Link
            href="/dashboard"
            className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
          >
            Dashboard →
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Submit a Support Request</h1>
          <p className="text-gray-500 mt-1">
            Our AI support agent will respond within seconds. For urgent issues,
            your request will be escalated to a human specialist.
          </p>
        </div>

        <SupportForm />

        {/* Other channels */}
        <div className="mt-8 bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Other ways to reach us</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>✉️</span>
              <span>support@techcorp.pk</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>💬</span>
              <span>WhatsApp: +92-300-TECHCORP</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-3">
            AI available 24/7 · Human agents: 9am–6pm PKR, Mon–Fri
          </p>
        </div>
      </main>
    </div>
  );
}
