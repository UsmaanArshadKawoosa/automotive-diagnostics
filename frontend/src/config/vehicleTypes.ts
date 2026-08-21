export type VehicleType = 'hatchback' | 'sedan' | 'suv' | 'pickup' | 'van';

export interface VehicleTypeConfig {
  type: VehicleType;
  label: string;
  description: string;
  modelAsset: string | null;
  fallbackModelAsset: string | null;
}

export const VEHICLE_TYPE_CONFIG: Record<VehicleType, VehicleTypeConfig> = {
  hatchback: {
    type: 'hatchback',
    label: 'Hatchback',
    description: 'Compact hatchback with front-engine layout',
    modelAsset: '/models/hatchback.glb',
    fallbackModelAsset: null,
  },
  sedan: {
    type: 'sedan',
    label: 'Sedan',
    description: 'Standard sedan with front-engine layout',
    modelAsset: '/models/sedan_detailed.glb',
    fallbackModelAsset: '/models/sedan.glb',
  },
  suv: {
    type: 'suv',
    label: 'SUV',
    description: 'Sport utility vehicle with higher ground clearance',
    modelAsset: '/models/suv.glb',
    fallbackModelAsset: null,
  },
  pickup: {
    type: 'pickup',
    label: 'Pickup',
    description: 'Light truck with open cargo bed',
    modelAsset: '/models/pickup.glb',
    fallbackModelAsset: null,
  },
  van: {
    type: 'van',
    label: 'Van',
    description: 'Enclosed box-style body',
    modelAsset: '/models/van.glb',
    fallbackModelAsset: null,
  },
};

export const VEHICLE_TYPES: VehicleType[] = ['hatchback', 'sedan', 'suv', 'pickup', 'van'];

export function getVehicleTypeConfig(vehicleType: VehicleType): VehicleTypeConfig {
  return VEHICLE_TYPE_CONFIG[vehicleType];
}
