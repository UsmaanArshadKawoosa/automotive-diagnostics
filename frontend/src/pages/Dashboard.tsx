import { Link } from 'react-router-dom';
import { Card, CardHeader, CardBody } from '../components/Card';
import { cn } from '../utils/cn';

export function Dashboard() {
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Automotive Diagnostic Engine</h1>
        <p className="mt-2 text-slate-600">
          AI-powered diagnostic reasoning for vehicle symptoms and DTC codes.
          Enter your vehicle information and symptoms to receive structured diagnostic hypotheses.
        </p>
      </section>

      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="New Diagnosis"
          description="Start a new diagnostic analysis"
          href="/diagnose"
          icon={
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          }
        />
        <StatCard
          title="Session History"
          description="Review past diagnostic sessions"
          href="/sessions"
          icon={
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          }
        />
        <StatCard
          title="Analytics"
          description="View diagnostic outcome statistics"
          href="/analytics"
          icon={
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-2.25A1.125 1.125 0 013 15.375v-2.25zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125v-8.25zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          }
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="How It Works" />
          <CardBody>
            <ol className="space-y-4 text-sm text-slate-600">
              {[
                'Enter your vehicle make, model, year, and any DTC codes',
                'Describe the symptoms you are experiencing',
                'The engine retrieves relevant knowledge and generates hypotheses',
                'Review the hypotheses, confidence scores, and recommended checks',
                'Track outcomes by updating hypothesis status and check results',
              ].map((step, idx) => (
                <li key={idx} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                    {idx + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Severity Levels" />
          <CardBody>
            <div className="space-y-3">
              {[
                { severity: 'low', label: 'Low', desc: 'Minor issue. Monitor and address at next service.', dot: 'bg-green-500 ring-green-500/20' },
                { severity: 'medium', label: 'Medium', desc: 'Should be addressed soon to prevent escalation.', dot: 'bg-amber-500 ring-amber-500/20' },
                { severity: 'high', label: 'High', desc: 'Urgent attention required. Address promptly.', dot: 'bg-red-500 ring-red-500/20' },
                { severity: 'critical', label: 'Critical', desc: 'Immediate action required. Do not drive until resolved.', dot: 'bg-red-900 ring-red-900/20' },
              ].map((item) => (
                <div key={item.severity} className="flex items-center gap-3">
                  <span className={cn('inline-flex h-2.5 w-2.5 rounded-full ring-4', item.dot)} />
                  <div>
                    <span className="text-sm font-semibold text-slate-900">{item.label}</span>
                    <span className="text-sm text-slate-500"> - {item.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </section>
    </div>
  );
}

function StatCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
}) {
  return (
    <Link to={href} className="group block">
      <Card className="transition-shadow hover:shadow-md">
        <CardBody>
          <div className="flex items-start justify-between">
            <div className="rounded-lg bg-brand-50 p-2 text-brand-600 group-hover:bg-brand-100 transition-colors">
              {icon}
            </div>
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </CardBody>
      </Card>
    </Link>
  );
}
