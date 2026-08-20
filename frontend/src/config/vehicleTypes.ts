export type VehicleType = 'hatchback' | 'sedan' | 'suv' | 'pickup' | 'van';

export interface VehicleTypeConfig {
  type: VehicleType;
  label: string;
  description: string;
  modelAsset: string | null;
}

export const VEHICLE_TYPE_CONFIG: Record<VehicleType, VehicleTypeConfig> = {
  hatchback: {
    type: 'hatchback',
    label: 'Hatchback',
    description: 'Compact hatchback with front-engine layout',
    modelAsset: null,
  },
  sedan: {
    type: 'sedan',
    label: 'Sedan',
    description: 'Standard sedan with front-engine layout',
    modelAsset: null,
  },
  suv: {
    type: 'suv',
    label: 'SUV',
    description: 'Sport utility vehicle with higher ground clearance',
    modelAsset: null,
  },
  pickup: {
    type: 'pickup',
    label: 'Pickup',
    description: 'Light truck with open cargo bed',
    modelAsset: null,
  },
  van: {
    type: 'van',
    label: 'Van',
    description: ' enclosed box-style body',
    modelAsset: null,
  },
};

export const VEHICLE_TYPES: VehicleType[] = ['hatchback', 'sedan', 'suv', 'pickup', 'van'];

export function getVehicleTypeConfig(vehicleType: VehicleType): VehicleTypeConfig {
  return VEHICLE_TYPE_CONFIG[vehicleType];
}
