import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DtcInput } from '../components/DtcInput';
import { HypothesisCard } from '../components/DiagnosticResults';
import { CheckOutcomeSection } from '../components/DiagnosticResults';
import { Vehicle3DViewer } from '../components/Vehicle3DViewer';
import { VEHICLE_TYPES, VEHICLE_TYPE_CONFIG, getVehicleTypeConfig } from '../config/vehicleTypes';
import type { DiagnosticCheckOutcome } from '../types/api';
import type { VehicleType } from '../types/api';

describe('DtcInput', () => {
  it('adds a valid DTC code', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DtcInput codes={[]} onChange={onChange} />);

    const input = screen.getByPlaceholderText('e.g. P0300');
    await user.type(input, 'P0300{Enter}');

    expect(onChange).toHaveBeenCalledWith(['P0300']);
  });

  it('removes a DTC code', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DtcInput codes={['P0300']} onChange={onChange} />);

    const removeBtn = screen.getByLabelText('Remove P0300');
    await user.click(removeBtn);

    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('rejects invalid DTC format', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DtcInput codes={[]} onChange={onChange} />);

    const input = screen.getByPlaceholderText('e.g. P0300');
    await user.type(input, 'INVALID{Enter}');

    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('HypothesisCard', () => {
  const defaultHypothesis = {
    fault_description: 'Faulty Spark Plugs',
    confidence_score: 0.8,
    severity: 'high' as const,
    supporting_evidence: ['[dtc] P0300'],
    recommended_checks: ['Inspect spark plugs'],
    repair_suggestion: 'Replace spark plugs',
  };

  it('renders fault description and confidence', () => {
    render(
      <HypothesisCard
        hypothesis={defaultHypothesis}
        resultId="result-1"
        currentStatus="proposed"
        onUpdateStatus={vi.fn()}
        updating={false}
      />
    );

    expect(screen.getByText('Faulty Spark Plugs')).toBeDefined();
    expect(screen.getByText('80%')).toBeDefined();
    expect(screen.getByText('Replace spark plugs')).toBeDefined();
  });

  it('calls onUpdateStatus when status button clicked', async () => {
    const user = userEvent.setup();
    const onUpdateStatus = vi.fn();
    render(
      <HypothesisCard
        hypothesis={defaultHypothesis}
        resultId="result-1"
        currentStatus="proposed"
        onUpdateStatus={onUpdateStatus}
        updating={false}
      />
    );

    await user.click(screen.getByText('Confirmed'));
    expect(onUpdateStatus).toHaveBeenCalledWith('result-1', 'confirmed');
  });
});

describe('CheckOutcomeSection', () => {
  const mockChecks: DiagnosticCheckOutcome[] = [
    {
      id: 'check-1',
      result_id: 'result-1',
      check_description: 'Inspect spark plugs',
      status: 'recommended',
      observed_result: null,
      technician_note: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  it('renders existing checks', () => {
    render(
      <CheckOutcomeSection
        resultId="result-1"
        checks={mockChecks}
        onCreateCheck={vi.fn()}
        onUpdateCheck={vi.fn()}
        loading={false}
      />
    );

    expect(screen.getByText('Inspect spark plugs')).toBeDefined();
  });

  it('shows pending recommended checks', () => {
    render(
      <CheckOutcomeSection
        resultId="result-1"
        checks={mockChecks}
        recommended_checks={['Inspect spark plugs', 'Perform compression test']}
        onCreateCheck={vi.fn()}
        onUpdateCheck={vi.fn()}
        loading={false}
      />
    );

    expect(screen.getByText('Perform compression test')).toBeDefined();
    expect(screen.getByText('Start Check')).toBeDefined();
  });

  it('creates check from recommendation', async () => {
    const user = userEvent.setup();
    const onCreateCheck = vi.fn();
    render(
      <CheckOutcomeSection
        resultId="result-1"
        checks={[]}
        recommended_checks={['Inspect vacuum lines']}
        onCreateCheck={onCreateCheck}
        onUpdateCheck={vi.fn()}
        loading={false}
      />
    );

    await user.click(screen.getByText('Start Check'));
    expect(onCreateCheck).toHaveBeenCalledWith('result-1', 'Inspect vacuum lines');
  });
});

describe('HypothesisCard component metadata', () => {
  const baseHypothesis = {
    fault_description: 'Faulty Spark Plugs',
    confidence_score: 0.8,
    severity: 'high' as const,
    supporting_evidence: ['[dtc] P0300'],
    recommended_checks: ['Inspect spark plugs'],
    repair_suggestion: 'Replace spark plugs',
  };

  it('renders component metadata when provided', () => {
    render(
      <HypothesisCard
        hypothesis={{
          ...baseHypothesis,
          component_id: 'spark_plug',
          system_category: 'ignition',
          vehicle_region: 'engine_bay',
        }}
        resultId="result-1"
        currentStatus="proposed"
        onUpdateStatus={vi.fn()}
        updating={false}
      />
    );

    expect(screen.getByText('spark plug')).toBeDefined();
    expect(screen.getByText('ignition')).toBeDefined();
    expect(screen.getByText('engine bay')).toBeDefined();
  });

  it('does not render component section when metadata is absent', () => {
    render(
      <HypothesisCard
        hypothesis={baseHypothesis}
        resultId="result-1"
        currentStatus="proposed"
        onUpdateStatus={vi.fn()}
        updating={false}
      />
    );

    expect(screen.queryByText('Component')).toBeNull();
  });
});

describe('Vehicle3DViewer', () => {
  it('renders with default vehicle type', () => {
    render(<Vehicle3DViewer />);
    expect(screen.getByText('3D Vehicle Visualization')).toBeDefined();
    expect(screen.getByText('Vehicle type: sedan')).toBeDefined();
  });

  it('renders custom vehicle type', () => {
    render(<Vehicle3DViewer vehicleType="suv" />);
    expect(screen.getByText('Vehicle type: suv')).toBeDefined();
  });

  it('renders highlighted components as selectable buttons', () => {
    render(
      <Vehicle3DViewer
        vehicleType="hatchback"
        highlightedComponents={[
          { component_id: 'ignition_coil', system_category: 'ignition', vehicle_region: 'engine_bay' },
        ]}
      />
    );

    expect(screen.getByText('Vehicle type: hatchback')).toBeDefined();
    const button = screen.getByRole('button', { name: 'ignition coil' });
    expect(button).toBeDefined();
  });

  it('selects a component when a highlighted button is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <Vehicle3DViewer
        vehicleType="sedan"
        highlightedComponents={[
          { component_id: 'ignition_coil', system_category: 'ignition', vehicle_region: 'engine_bay' },
        ]}
        onComponentSelect={onSelect}
      />
    );

    await user.click(screen.getByRole('button', { name: 'ignition coil' }));
    expect(onSelect).toHaveBeenCalledWith({
      component_id: 'ignition_coil',
      system_category: 'ignition',
      vehicle_region: 'engine_bay',
    });
  });

  it('renders selected component', () => {
    render(
      <Vehicle3DViewer
        vehicleType="sedan"
        selectedComponent={{ component_id: 'catalytic_converter', system_category: 'exhaust', vehicle_region: 'underbody' }}
      />
    );

    expect(screen.getByText('Selected: catalytic converter')).toBeDefined();
  });

  it('does not render highlighted section when no components provided', () => {
    render(<Vehicle3DViewer vehicleType="sedan" highlightedComponents={[]} />);
    expect(screen.queryByText('Highlighted')).toBeNull();
  });
});

describe('vehicle type configuration', () => {
  it('exposes the five generic vehicle types', () => {
    expect(VEHICLE_TYPES).toEqual(['hatchback', 'sedan', 'suv', 'pickup', 'van']);
    (['hatchback', 'sedan', 'suv', 'pickup', 'van'] as VehicleType[]).forEach((vt) => {
      expect(VEHICLE_TYPE_CONFIG[vt]).toBeDefined();
      expect(VEHICLE_TYPE_CONFIG[vt].modelAsset).toBeDefined();
      expect(VEHICLE_TYPE_CONFIG[vt].modelAsset).toBeTruthy();
    });
    expect(VEHICLE_TYPE_CONFIG.hatchback.modelAsset).toBe('/models/hatchback.glb');
    expect(VEHICLE_TYPE_CONFIG.sedan.modelAsset).toBe('/models/sedan_detailed.glb');
    expect(VEHICLE_TYPE_CONFIG.sedan.fallbackModelAsset).toBe('/models/sedan.glb');
    expect(VEHICLE_TYPE_CONFIG.suv.modelAsset).toBe('/models/suv.glb');
    expect(VEHICLE_TYPE_CONFIG.pickup.modelAsset).toBe('/models/pickup.glb');
    expect(VEHICLE_TYPE_CONFIG.van.modelAsset).toBe('/models/van.glb');
  });

  it('returns config for a known vehicle type', () => {
    expect(getVehicleTypeConfig('suv').label).toBe('SUV');
  });
});

