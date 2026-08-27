import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { HypothesisCard } from '../components/DiagnosticResults';
import { MechanicSummary } from '../pages/DiagnosePage';
import { DiagnosePage } from '../pages/DiagnosePage';
import type { DiagnosticHypothesis } from '../types/api';

const richHypothesis = {
  fault_description: 'Worn brake pads contacting rotor',
  confidence_score: 0.62,
  severity: 'high' as const,
  supporting_evidence: ['Pad material worn below minimum thickness'],
  recommended_checks: ['Inspect brake pad thickness', 'Measure rotor runout'],
  repair_suggestion: 'Replace brake pads and inspect rotor',
  component_id: 'brake_pad',
  system_category: 'brakes',
  vehicle_region: 'underbody',
  safety_tier: 'diy_repair' as const,
  safety_tier_label: 'DIY repair may be possible',
  safety_tier_description: 'Owner can replace pads with basic tools',
  safety_tier_reasoning: ['Non-hazardous system when wheels are secured'],
  differential_rank: 1,
  knowledge_references: [],
  evidence_references: [],
  diy_repair: {
    suitable: true,
    suitability: 'Recommended for DIY',
    difficulty: 'moderate' as const,
    estimated_time: '2 hours',
    tools: ['Socket set', 'Torque wrench'],
    parts: ['Brake pads', 'Hardware kit'],
    safety_warnings: ['Secure the vehicle on jack stands'],
    preparation_steps: ['Loosen lug nuts', 'Lift vehicle'],
    steps: ['Remove wheel', 'Compress caliper piston'],
    verification_steps: ['Pump brake pedal', 'Test drive carefully'],
    professional_help_conditions: ['If the rotor is cracked'],
  },
  resources: [
    { type: 'guide', title: 'Brake pad replacement guide', source: 'RepairManual', url: 'https://example.com/guide' },
    { type: 'youtube', title: 'How to replace brake pads', source: 'YouTube', url: 'https://youtube.com/watch?v=abc123' },
  ],
} satisfies DiagnosticHypothesis;

const renderCard = (hypothesis: Partial<DiagnosticHypothesis>) =>
  render(
    <HypothesisCard
      hypothesis={hypothesis as DiagnosticHypothesis}
      resultId="r1"
      currentStatus="proposed"
      onUpdateStatus={vi.fn()}
      updating={false}
    />
  );

describe('Diagnostic report richness (regression)', () => {
  it('renders recommended checks, tools, parts, steps, safety, pro conditions, and resources', () => {
    renderCard(richHypothesis);

    // Recommended checks
    expect(screen.getByText('Inspect brake pad thickness')).toBeDefined();
    // Tools
    expect(screen.getByText('Socket set')).toBeDefined();
    expect(screen.getByText('Torque wrench')).toBeDefined();
    // Parts
    expect(screen.getByText('Brake pads')).toBeDefined();
    expect(screen.getByText('Hardware kit')).toBeDefined();
    // Preparation / repair / verification steps
    expect(screen.getByText('Loosen lug nuts')).toBeDefined();
    expect(screen.getByText('Remove wheel')).toBeDefined();
    expect(screen.getByText('Pump brake pedal')).toBeDefined();
    // Safety warnings
    expect(screen.getByText('Secure the vehicle on jack stands')).toBeDefined();
    // Professional-help conditions
    expect(screen.getByText('If the rotor is cracked')).toBeDefined();
    // Resources (guide + youtube with Watch label)
    expect(screen.getByText('Brake pad replacement guide')).toBeDefined();
    expect(screen.getByText('How to replace brake pads')).toBeDefined();
    expect(screen.getByText(/Watch Guide/)).toBeDefined();
  });

  it('hides the resources section when none are provided', () => {
    const { container } = renderCard({ ...richHypothesis, resources: [] });
    expect(screen.queryByText('Helpful Resources')).toBeNull();
    expect(container.innerHTML).not.toContain('youtube.com');
  });

  it('does not crash when diy_repair is null', () => {
    const { container } = renderCard({ ...richHypothesis, diy_repair: null });
    expect(screen.queryByText('DIY Repair Guide')).toBeNull();
    expect(container).toBeDefined();
  });

  it('does not crash and hides difficulty when difficulty is null', () => {
    const { container } = renderCard({
      ...richHypothesis,
      diy_repair: { ...richHypothesis.diy_repair!, suitable: true, difficulty: null },
    });
    // Section still present (suitable), difficulty badge absent
    expect(screen.getByText('DIY Repair Guide')).toBeDefined();
    expect(screen.queryByText('Moderate')).toBeNull();
    expect(container).toBeDefined();
  });

  it('renders multiple hypotheses from a differential', () => {
    const { getAllByText } = render(
      <div>
        <HypothesisCard hypothesis={{ ...richHypothesis, fault_description: 'Cause A' } as DiagnosticHypothesis} resultId="a" currentStatus="proposed" onUpdateStatus={vi.fn()} updating={false} />
        <HypothesisCard hypothesis={{ ...richHypothesis, fault_description: 'Cause B', diy_repair: null } as DiagnosticHypothesis} resultId="b" currentStatus="proposed" onUpdateStatus={vi.fn()} updating={false} />
      </div>
    );
    expect(getAllByText('Cause A').length).toBeGreaterThan(0);
    expect(getAllByText('Cause B').length).toBeGreaterThan(0);
  });

  it('Mechanic-Ready summary includes detailed backend data without empty sections', () => {
    render(
      <MechanicSummary
        vehicleContext="Sedan"
        symptomText="My car makes a grinding noise when braking."
        hypotheses={[richHypothesis]}
      />
    );
    const pre = screen.getByText(/AUTOMOTIVE DIAGNOSTIC SUMMARY/).closest('pre')!;
    const text = pre.textContent || '';
    expect(text).toContain('Recommended checks:');
    expect(text).toContain('Tools: Socket set, Torque wrench');
    expect(text).toContain('Parts: Brake pads, Hardware kit');
    expect(text).toContain('Preparation:');
    expect(text).toContain('Verification:');
    expect(text).toContain('Safety warnings:');
    expect(text).toContain('https://example.com/guide');
    expect(text).toContain('https://youtube.com/watch?v=abc123');
  });
});

describe('Diagnose input validation (regression)', () => {
  it('rejects an empty symptom', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <DiagnosePage />
      </MemoryRouter>
    );
    await user.click(screen.getByText('Diagnose Vehicle'));
    expect(screen.getByText(/Please describe what's happening with your vehicle/i)).toBeDefined();
  });

  it('rejects a whitespace-only symptom', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <DiagnosePage />
      </MemoryRouter>
    );
    const textarea = screen.getByPlaceholderText(/Example: My car shakes/i);
    await user.type(textarea, '     ');
    await user.click(screen.getByText('Diagnose Vehicle'));
    expect(screen.getByText(/Please describe what's happening with your vehicle/i)).toBeDefined();
  });
});
