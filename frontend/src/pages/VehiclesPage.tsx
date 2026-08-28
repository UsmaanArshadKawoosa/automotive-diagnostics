import { Link } from 'react-router-dom';
import { Card, CardBody } from '../components/Card';
import { VEHICLE_TYPE_CONFIG, VEHICLE_TYPES } from '../config/vehicleTypes';

export function VehiclesPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8">
        <h1 className="font-headline-lg text-2xl font-bold text-on-surface sm:text-3xl">Vehicles</h1>
        <p className="mt-1 text-on-surface-variant">
          Supported body styles for 3D visualization and diagnostic modeling.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {VEHICLE_TYPES.map((type) => {
          const config = VEHICLE_TYPE_CONFIG[type];
          return (
            <Card key={type} className="overflow-hidden">
              <div className="flex items-center gap-3 border-b border-outline-variant bg-surface-container-low px-4 py-3">
                <span className="material-symbols-outlined text-primary">directions_car</span>
                <div>
                  <p className="font-medium text-on-surface">{config.label}</p>
                  <p className="text-xs text-on-surface-variant">{config.description}</p>
                </div>
              </div>
              <CardBody className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-on-surface-variant">3D model</span>
                  <span className="font-data-mono text-xs text-on-surface">{config.modelAsset?.split('/').pop()}</span>
                </div>
                <Link
                  to="/diagnose"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-fixed-dim"
                >
                  Start diagnosis
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </Link>
              </CardBody>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
