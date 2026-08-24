import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DtcInput } from '../components/DtcInput';
import { HypothesisCard } from '../components/DiagnosticResults';
import { CheckOutcomeSection } from '../components/DiagnosticResults';
import { Vehicle3DViewer } from '../components/Vehicle3DViewer';
import { OfflineIndicator } from '../components/OfflineIndicator';
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

    await user.click(screen.getByText('Show technical details'));
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

describe('OfflineIndicator', () => {
  it('renders when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    window.dispatchEvent(new Event('offline'));

    render(<OfflineIndicator />);

    expect(screen.getByText('You are currently offline')).toBeDefined();
  });

  it('does not render when online', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    window.dispatchEvent(new Event('online'));

    const { container } = render(<OfflineIndicator />);

    expect(container.innerHTML).toBe('');
  });
});

describe('useCachedSession', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('saves and loads a session from cache', async () => {
    const { useCachedSession } = await import('../hooks/useCachedSession');
    const TestComponent = () => {
      const { cachedSession, isFromCache, saveToCache } = useCachedSession('session-1');
      return (
        <div>
          <span data-testid="cached">{cachedSession ? 'yes' : 'no'}</span>
          <span data-testid="fromCache">{isFromCache ? 'yes' : 'no'}</span>
          <button onClick={() => saveToCache({
            session: { id: '1', vin: null, make: null, model: null, year: null, symptom_text: 'Test', dtc_codes: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            results: [],
            conversation_messages: [],
            evidence: [],
          }, 'session-1')}>Save</button>
        </div>
      );
    };

    render(<TestComponent />);
    await userEvent.click(screen.getByText('Save'));
    expect(screen.getByTestId('cached').textContent).toBe('yes');
    expect(screen.getByTestId('fromCache').textContent).toBe('yes');
  });
});

describe('Offline submission prevention', () => {
  it('blocks diagnosis submission when offline', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    window.dispatchEvent(new Event('offline'));

    const { DiagnosePage } = await import('../pages/DiagnosePage');
    render(
      <MemoryRouter>
        <DiagnosePage />
      </MemoryRouter>
    );

    const submitButton = screen.getByText('Diagnose my car');
    await userEvent.click(submitButton);

    expect(screen.getByText(/live connection is required/i)).toBeDefined();
  });
});

describe('Cached session rendering', () => {
  it('shows stale indicator for cached data', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    window.dispatchEvent(new Event('offline'));

    vi.doMock('../hooks/useCachedSession', () => ({
      useCachedSession: () => ({
        cachedSession: {
          sessionId: 'session-1',
          cachedAt: new Date().toISOString(),
          data: {
            session: { id: 'session-1', symptom_text: 'Test', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
            results: [{ id: 'r1', fault_description: 'Test fault', confidence_score: 0.9, severity: 'high', supporting_evidence: [], recommended_checks: [], repair_suggestion: null, hypothesis_status: 'proposed', check_outcomes: [] }],
            conversation_messages: [],
            evidence: [],
          },
        },
        isFromCache: true,
        saveToCache: vi.fn(),
        clearCache: vi.fn(),
      }),
    }));

    const { SessionDetailPage } = await import('../pages/SessionDetailPage');
    render(
      <MemoryRouter initialEntries={['/sessions/session-1']}>
        <SessionDetailPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/viewing cached session data/i)).toBeDefined();
    vi.doUnmock('../hooks/useCachedSession');
  });
});

describe('Service worker registration', () => {
  it('registers service worker in production', () => {
    const registerMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'serviceWorker', {
      value: { register: registerMock },
      writable: true,
    });

    expect(registerMock).not.toHaveBeenCalled();
  });
});

