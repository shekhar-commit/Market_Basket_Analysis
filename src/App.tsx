import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CalendarDays, RefreshCw } from 'lucide-react';
import { DashboardHeader, TopSellingProducts, ComboIntelligenceDashboard } from './components.tsx';
import type {
  DateRangeFilter,
  HistoricalComboCandidate,
  ProductSalesStat,
  StockStatus,
} from './components.tsx';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface RestaurantInfo {
  restaurant_name: string;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || result.error || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [dateFilter, setDateFilter] = useState<DateRangeFilter>('30days');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [activeSection, setActiveSection] = useState('dashboard');
  const [restaurantName, setRestaurantName] = useState('Restaurant');
  const [products, setProducts] = useState<ProductSalesStat[]>([]);
  const [combos, setCombos] = useState<HistoricalComboCandidate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (dateFilter === 'custom' && !startDate) {
      setProducts([]);
      setCombos([]);
      setIsLoading(false);
      setError('Choose a start date for the custom range.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ filter: dateFilter });
      if (dateFilter === 'custom') {
        params.set('start_date', startDate);
        if (endDate) params.set('end_date', endDate);
      }

      const [productData, comboData, restaurant] = await Promise.all([
        getJson<Array<Omit<ProductSalesStat, 'image_emoji'> & { image_emoji?: string }>>(
          `/api/products/top-selling?${new URLSearchParams({
            filter: dateFilter,
            start_date: dateFilter === 'custom' ? startDate : '',
            end_date: dateFilter === 'custom' ? endDate : '',
            limit: '10',
          }).toString()}`,
        ),
        getJson<HistoricalComboCandidate[]>(`/api/combos?${params.toString()}`),
        getJson<RestaurantInfo>('/api/restaurants/R001'),
      ]);
      setProducts(productData.map(product => ({ ...product, image_emoji: product.image_emoji ?? '' })));
      setCombos(comboData);
      setRestaurantName(restaurant.restaurant_name);
    } catch (loadError) {
      console.error('Failed to load restaurant sales data', loadError);
      setError(loadError instanceof Error ? loadError.message : 'Failed to load restaurant sales data.');
    } finally {
      setIsLoading(false);
    }
  }, [dateFilter, endDate, startDate]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const navigateTo = (section: string) => {
    setActiveSection(section);
    document.getElementById(section)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <DashboardHeader
        dateFilter={dateFilter}
        setDateFilter={setDateFilter}
        restaurantName={restaurantName}
        isLoading={isLoading}
        onRefresh={() => void loadData()}
        activeSection={activeSection}
        onNavigate={navigateTo}
      />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        {dateFilter === 'custom' && (
          <section className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <label className="text-xs text-slate-300">
              <span className="mb-1 block">Start date</span>
              <input
                type="date"
                value={startDate}
                max={endDate || undefined}
                onChange={event => setStartDate(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
            <label className="text-xs text-slate-300">
              <span className="mb-1 block">End date</span>
              <input
                type="date"
                value={endDate}
                min={startDate || undefined}
                onChange={event => setEndDate(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
            <span className="flex items-center gap-2 pb-2 text-xs text-slate-500">
              <CalendarDays className="h-4 w-4" />
              End date is inclusive
            </span>
          </section>
        )}

        {error && (
          <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
            <span className="flex items-center gap-2"><AlertCircle className="h-4 w-4 shrink-0" />{error}</span>
            <button
              type="button"
              onClick={() => void loadData()}
              className="flex shrink-0 items-center gap-2 rounded-lg bg-rose-500/15 px-3 py-2 font-medium hover:bg-rose-500/25"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>
          </div>
        )}

        <section id="dashboard" className="scroll-mt-28">
          <div className="mb-4">
            <h2 className="text-xl font-bold text-white">Restaurant Sales</h2>
            <p className="mt-1 text-sm text-slate-400">
              Actual transaction history for the selected date range
            </p>
          </div>
          <TopSellingProducts products={products} />
        </section>

        <ComboIntelligenceDashboard combos={combos} isLoading={isLoading} />
        <p className="pb-4 text-center text-xs text-slate-500">
          Combo prices and profits are estimates based on current menu costs; actual sales results may vary.
        </p>
      </main>
    </div>
  );
}

export type OrderChannel = 'all' | 'dine_in' | 'takeaway' | 'delivery' | 'online';

export type OrderStatus = 'all' | 'completed' | 'cancelled' | 'refunded';

export type RecommendationMode = 'ml_hybrid' | 'rule_based';

export type DataStatus = 'sufficient' | 'insufficient';

export interface Restaurant {
  restaurant_id: string;
  restaurant_name: string;
  timezone: string;
  currency: string;
  created_at: string;
  is_active: boolean;
}

export interface Product {
  product_id: string;
  restaurant_id: string;
  product_name: string;
  category: string;
  selling_price: number;
  cost_price: number;
  profit_per_unit: number;
  profit_margin: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  image_emoji: string;
}

export interface InventoryItem {
  product_id: string;
  product_name: string;
  current_stock: number;
  minimum_stock: number;
  reorder_level: number;
  is_available: boolean;
  last_updated: string;
}

export interface TransactionItem {
  transaction_id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  net_price: number;
  total_price: number;
}

export interface Transaction {
  transaction_id: string;
  restaurant_id: string;
  customer_id?: string;
  transaction_date: string;
  transaction_time: string;
  total_amount: number;
  discount_amount: number;
  order_status: 'completed' | 'cancelled' | 'refunded';
  payment_status: 'paid' | 'pending' | 'failed';
  channel: 'dine_in' | 'takeaway' | 'delivery' | 'online';
  timestamp: string;
  created_at: string;
  items: TransactionItem[];
}

export interface PopularProductStat {
  product_id: string;
  product_name: string;
  category: string;
  image_emoji: string;
  total_quantity_sold: number;
  total_orders: number;
  unique_orders: number;
  revenue: number;
  average_price: number | null;
  sales_share: number;
  recent_quantity_sold: number;
  recent_order_count: number;
  recent_revenue: number;
}

export interface ComboCandidateProduct {
  product_id: string;
  name: string;
  quantity: number;
  selling_price: number | null;
  cost_price: number | null;
  current_stock: number | null;
  available: boolean | null;
}

export interface RestaurantComboCandidate {
  combo_id: string;
  restaurant_id: string;
  products: ComboCandidateProduct[];
  individual_price: number | null;
  combo_discount_percentage: number | null;
  maximum_safe_discount_percentage: number | null;
  combo_price: number | null;
  total_cost: number | null;
  profit: number | null;
  profit_margin_percentage: number | null;
  support: number;
  confidence: number;
  confidence_antecedent_product_ids: string[];
  confidence_consequent_product_id: string;
  lift: number;
  orders_together: number;
  recent_orders_together_7d: number;
  recent_orders_together_30d: number;
  profit_available: boolean;
  availability_status: 'available' | 'unknown' | 'unavailable';
  is_recommended: boolean;
  recommendation_reason: string;
  explanation: string;
  profit_unavailable_reason?: string;
}

export interface RestaurantComboSummary {
  restaurant_id: string;
  period: { start: string | null; end: string | null };
  top_selling_products: PopularProductStat[];
  combo_candidates: RestaurantComboCandidate[];
  suggested_combos: RestaurantComboCandidate[];
  recent_popular_combos: RestaurantComboCandidate[];
  profit_opportunities: RestaurantComboCandidate[];
  summary: {
    orders_analyzed: number;
    products_analyzed: number;
    combo_candidates: number;
    invalid_rows: number;
  };
  message: string | null;
}

export interface FeatureContribution {
  feature: string;
  label: string;
  impact: 'positive' | 'neutral' | 'negative';
  weight: number; // percentage or relative impact
  explanation: string;
}

export interface ProductPairCombo {
  combo_id: string;
  restaurant_id: string;
  product_a_id: string;
  product_a_name: string;
  product_a_emoji: string;
  product_a_price: number;
  product_a_cost: number;
  product_a_orders: number;
  product_a_stock: number;

  product_b_id: string;
  product_b_name: string;
  product_b_emoji: string;
  product_b_price: number;
  product_b_cost: number;
  product_b_orders: number;
  product_b_stock: number;

  pair_transaction_count: number;
  total_transactions: number;

  // Association Discovery (All time / selected period)
  support: number; // e.g. 0.13 = 13%
  confidence_a_to_b: number; // e.g. 0.433 = 43.3%
  confidence_b_to_a: number; // e.g. 0.65 = 65%
  lift: number; // e.g. 2.17

  // Recent Association Metrics (e.g. last 7 or 14 days trend)
  recent_support: number;
  recent_confidence: number;
  recent_lift: number;
  lift_momentum: 'increasing' | 'stable' | 'decreasing';

  // Economics
  normal_price: number;
  suggested_combo_price: number;
  customer_saving: number;
  combo_cost: number;
  combo_profit: number;
  combo_margin: number;
  historical_pair_value: number;
  expected_monthly_orders: number;
  expected_monthly_revenue: number;
  expected_monthly_profit: number;

  // Phase 2: Future Performance Prediction & Regression
  predicted_future_combo_purchases_7d?: number | null;
  estimated_gross_profit_7d?: number | null;
  model_version?: string | null;

  // Operating Mode & Decision Logic
  recommendation_mode: RecommendationMode; // 'ml_hybrid' | 'rule_based'
  ml_score?: number; // 0-100 predicted success probability
  ml_confidence_label?: 'Very High' | 'High' | 'Moderate' | 'Low';
  rule_score: number; // 0-100 statistical heuristic score
  final_score: number;

  is_candidate_combo: boolean;
  recommendation_note: string;
  explanation_points: string[];
  feature_contributions?: FeatureContribution[];

  // Inventory & Stock Check
  stock_status: StockStatus;
  stock_warning?: string;

  // Channel distribution
  channel_distribution: {
    dine_in: number;
    takeaway: number;
    delivery: number;
    online: number;
  };
}

export interface FrequentlyBoughtCompanion {
  product_id: string;
  product_name: string;
  image_emoji: string;
  bought_together: number;
  confidence: number;
  lift: number;
  suggested_combo_price: number;
  combo_profit: number;
  stock_status: StockStatus;
}

export interface ManagerThresholds {
  min_pair_count: number; // default 20
  min_confidence: number; // default 0.25
  min_lift: number; // default 1.10
}

export interface DataSufficiencyThresholds {
  minimum_transactions_for_ml: number; // default 500
  minimum_historical_days: number; // default 14
  minimum_product_transactions: number; // default 15
  minimum_pair_transactions: number; // default 10
  minimum_valid_baskets: number; // default 300
  minimum_data_completeness: number; // default 85%
  simulation_mode_override: 'auto' | 'force_insufficient' | 'force_sufficient';
}

export interface CriteriaCheck {
  id: string;
  label: string;
  current_value: number | string;
  required_threshold: number | string;
  passed: boolean;
  description: string;
}

export interface DataSufficiencyReport {
  data_status: DataStatus; // 'sufficient' | 'insufficient'
  recommendation_mode: RecommendationMode; // 'ml_hybrid' | 'rule_based'
  total_transactions: number;
  valid_baskets: number;
  filtered_cancelled_orders: number;
  unique_products_count: number;
  historical_days_span: number;
  data_completeness_pct: number;
  duplicate_rate_pct: number;
  cancelled_refunded_rate_pct: number;
  avg_transactions_per_product: number;
  avg_pair_transactions: number;
  criteria_checks: CriteriaCheck[];
  summary_message: string;
}

export interface ComboModelMetadata {
  model_id: string;
  restaurant_id: string;
  model_type: string;
  trained_at: string;
  training_records_count: number;
  validation_accuracy: number;
  auc_roc: number;
  data_sufficiency_status: DataStatus;
  feature_list: string[];
  status: 'active' | 'paused_insufficient_data' | 'retraining';
}

export interface AssociationRule {
  rule_id: string;
  antecedent_id: string;
  antecedent_name: string;
  antecedent_emoji: string;
  antecedent_category: string;
  consequent_id: string;
  consequent_name: string;
  consequent_emoji: string;
  consequent_category: string;
  pair_count: number;
  total_baskets: number;
  support: number;
  confidence: number;
  lift: number;
}

export interface DashboardSummary {
  total_orders: number;
  total_revenue: number;
  total_profit: number;
  top_product: {
    product_name: string;
    image_emoji: string;
    quantity_sold: number;
    revenue: number;
  } | null;
  top_combo: {
    title: string;
    bought_together: number;
    lift: number;
    profit: number;
  } | null;
  date_filter: DateRangeFilter;
  date_range_label: string;
  channel_filter: OrderChannel;
  active_algorithm: 'FP-Growth' | 'Apriori';
  data_sufficiency: DataSufficiencyReport;
  model_metadata: ComboModelMetadata;
}

export interface ModelStatusResponse {
  mode: 'ML_ACTIVE' | 'RULE_BASED' | 'TRAINING';
  status: 'ACTIVE' | 'TRAINING' | 'INSUFFICIENT_DATA' | 'READY_FOR_TRAINING';
  model_version: string | null;
  model_type: string | null;
  last_trained_at: string | null;
  training_transactions: number;
  new_transactions_since_training: number;
  retrain_threshold: number;
  next_retrain_trigger: string;
  mae: number | null;
  rmse: number | null;
  precision_at_10: number | null;
  active_job_id?: string | null;
  sufficient_for_ml: boolean;
}

export interface ModelMetricsResponse {
  has_active_model: boolean;
  model_version?: string;
  model_type?: string;
  target?: string;
  mae?: number;
  rmse?: number;
  mape?: number;
  r2?: number;
  precision_at_5?: number;
  precision_at_10?: number;
  training_samples?: number;
  training_transactions?: number;
  feature_names?: string[];
  training_date_range?: { start: string | null; end: string | null };
  validation_date_range?: { start: string | null; end: string | null };
  test_date_range?: { start: string | null; end: string | null };
  message?: string;
}

export interface ModelHistoryItem {
  model_id: string;
  model_version: string;
  model_type: string;
  status: 'ACTIVE' | 'ARCHIVED' | 'VALIDATED' | 'REJECTED' | 'TRAINING' | 'FAILED';
  target: string;
  training_samples: number;
  training_transactions: number;
  training_start_date: string | null;
  training_end_date: string | null;
  validation_start_date: string | null;
  validation_end_date: string | null;
  mae: number;
  rmse: number;
  mape: number;
  r2: number;
  precision_at_5: number;
  precision_at_10: number;
  created_at: string | null;
  promoted_at: string | null;
}

/* =========================================================
   PHASE 3: REAL-TIME RECOMMENDATION & CART INTERFACES
========================================================= */

export interface LiveCartItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  image_emoji?: string;
  category?: string;
}

export interface LiveCart {
  cart_id: string;
  restaurant_id: string;
  customer_id?: string | null;
  status: 'active' | 'completed' | 'abandoned';
  created_at: string;
  updated_at: string;
  items: LiveCartItem[];
  total_amount: number;
}

export interface RealtimeRecommendationItem {
  product_id: string;
  product_name: string;
  source_product_ids: string[];
  source_product_names: string[];
  score: number;
  confidence: number;
  lift: number;
  pair_transaction_count: number;
  current_stock: number;
  available: boolean;
  price: number;
  cost: number;
  combo_profit: number;
  profit_margin: number;
  ml_prediction?: number | null;
  recommendation_mode: 'ml' | 'rule_based';
  model_version?: string | null;
  reason: string;
  explanation: string;
  image_emoji?: string;
  category?: string;
}

export interface RecommendationTraceData {
  cart_products: string[];
  funnel: {
    '1_candidates_generated': number;
    '2_passed_association_quality': number;
    '3_passed_product_active': number;
    '4_passed_availability': number;
    '5_passed_in_stock': number;
    '6_passed_profit_gate': number;
    '7_final_ranked_returned': number;
  };
  dropped_samples?: Array<{
    product_id: string;
    product_name: string;
    stage: string;
    reason: string;
  }>;
}

export interface RealtimeRecommendationResponse {
  restaurant_id: string;
  cart_id?: string | null;
  recommendation_mode: 'ml' | 'rule_based' | 'insufficient_data';
  model_version?: string | null;
  latency_ms: number;
  recommendations: RealtimeRecommendationItem[];
  trace?: RecommendationTraceData;
}

export interface RecommendationFeedbackEvent {
  event_id: string;
  cart_id?: string | null;
  source_product_id?: string | null;
  recommended_product_id: string;
  recommended_product_name?: string;
  timestamp: string;
  shown: boolean;
  clicked: boolean;
  added_to_cart: boolean;
  purchased: boolean;
  price_at_event: number;
  model_version?: string | null;
  recommendation_mode: string;
}

export interface RecommendationMetricsData {
  restaurant_id: string;
  timeframe_days: number;
  shown_count: number;
  click_count: number;
  add_to_cart_count: number;
  purchase_count: number;
  ctr: number;
  add_to_cart_rate: number;
  purchase_conversion_rate: number;
  recent_events_count: number;
}

/* =========================================================
   PHASE 4: MONITORING, DRIFT, MODEL HEALTH & SYSTEM HEALTH
========================================================= */

export type HealthSeverity = 'HEALTHY' | 'WARNING' | 'CRITICAL';

export type ModelDegradationStatus = 'HEALTHY' | 'WARNING' | 'DEGRADED' | 'CRITICAL';

export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';

export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export type DriftMethod = 'psi' | 'ks' | 'js_divergence';

export type RetrainingTriggerType = 'DATA_DRIFT' | 'MODEL_DEGRADATION' | 'PREDICTION_DRIFT' | 'NEW_DATA_THRESHOLD' | 'MANUAL' | 'SCHEDULED';

export type RetrainingStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';

export interface SystemHealthReport {
  overall_status: HealthSeverity;
  data_status: HealthSeverity;
  model_status: HealthSeverity;
  recommendation_status: HealthSeverity;
  api_status: HealthSeverity;
  business_status: HealthSeverity;
  open_alerts: number;
  health_score: number; // 0-100 operational reliability score
  active_model_version: string | null;
  last_evaluated: string;
  summary_message: string;
}

export interface DataQualitySnapshot {
  snapshot_id: string;
  timestamp: string;
  data_completeness: number;
  transaction_count: number;
  valid_transaction_count: number;
  duplicate_rate: number;
  refund_rate: number;
  multi_item_baskets: number;
  unique_products: number;
}

export interface DataQualityMonitoringReport {
  status: HealthSeverity;
  data_completeness: number; // e.g. 0.984 = 98.4%
  total_transactions: number;
  valid_transactions: number;
  invalid_transactions: number;
  duplicate_transactions: number;
  duplicate_rate: number;
  cancelled_transactions: number;
  cancelled_rate: number;
  refunded_transactions: number;
  refund_rate: number;
  missing_product_count: number;
  missing_price_count: number;
  invalid_quantity_count: number;
  unknown_product_rate: number;
  invalid_price_rate: number;
  invalid_quantity_rate: number;
  historical_days_span: number;
  unique_products_count: number;
  multi_item_baskets: number;
  snapshots: DataQualitySnapshot[];
  thresholds: {
    completeness_warning: number;
    completeness_critical: number;
    max_duplicate_rate: number;
    max_invalid_rate: number;
  };
}

export interface FeatureDriftResult {
  feature_name: string;
  feature_type: 'numerical' | 'categorical';
  method: DriftMethod;
  reference_mean: number;
  current_mean: number;
  reference_std: number;
  current_std: number;
  drift_score: number; // PSI or KS statistic
  p_value?: number;
  status: HealthSeverity;
  sample_size: number;
  threshold_warning: number;
  threshold_critical: number;
}

export interface PredictionDriftResult {
  status: HealthSeverity;
  drift_score: number; // PSI of predictions
  prediction_mean_reference: number;
  prediction_mean_current: number;
  prediction_std_reference: number;
  prediction_std_current: number;
  distribution_bins: string[];
  reference_distribution: number[];
  current_distribution: number[];
  sample_size: number;
}

export interface DriftReport {
  restaurant_id: string;
  model_version: string;
  overall_status: HealthSeverity;
  reference_period: string;
  current_period: string;
  total_monitored_features: number;
  healthy_features_count: number;
  warning_features_count: number;
  critical_features_count: number;
  features: FeatureDriftResult[];
  prediction_drift: PredictionDriftResult;
}

export interface ModelPerformanceSnapshot {
  timestamp: string;
  model_version: string;
  sample_size: number;
  mae: number;
  rmse: number;
  mape: number;
}

export interface ModelHealthReport {
  restaurant_id: string;
  active_model_version: string;
  model_type: string;
  status: ModelDegradationStatus;
  trained_at: string;
  last_prediction_at: string;
  total_production_predictions: number;
  training_sample_size: number;
  validation_mae: number;
  production_mae: number;
  production_rmse: number;
  baseline_mae: number;
  mae_degradation_pct: number;
  consecutive_degradation_checks: number;
  drift_status: HealthSeverity;
  history: ModelPerformanceSnapshot[];
  model_versions: Array<{
    version: string;
    model_type: string;
    status: string;
    trained_at: string;
    validation_mae: number;
    production_mae: number | null;
    predictions_count: number;
    conversion_rate: number;
  }>;
}

export interface ProductRecPerformance {
  product_id: string;
  product_name: string;
  shown: number;
  clicks: number;
  adds: number;
  purchases: number;
  ctr: number;
  add_to_cart_rate: number;
  purchase_conversion: number;
  avg_profit: number;
  current_stock: number;
  is_available: boolean;
}

export interface ChannelRecPerformance {
  channel: string;
  shown: number;
  purchases: number;
  conversion_rate: number;
}

export interface RecommendationPerformanceReport {
  period: string;
  shown: number;
  clicks: number;
  adds: number;
  purchases: number;
  ctr: number;
  add_to_cart_rate: number;
  purchase_conversion: number;
  recommendation_coverage: number;
  fallback_rate: number;
  no_candidate_rate: number;
  sample_size: number;
  by_product: ProductRecPerformance[];
  by_channel: ChannelRecPerformance[];
  trend: Array<{
    date: string;
    shown: number;
    purchases: number;
    conversion: number;
    fallback_rate: number;
  }>;
}

export interface BusinessMonitoringReport {
  observed_recommended_revenue: number;
  observed_recommended_profit: number;
  total_restaurant_revenue: number;
  recommended_revenue_share_pct: number;
  avg_order_value_with_rec: number;
  avg_order_value_without_rec: number;
  stockout_after_rec_count: number;
  rec_stockout_rate: number;
  causality_disclaimer: string;
  ab_testing: {
    is_active: boolean;
    experiment_id?: string;
    control_sample_size: number;
    treatment_sample_size: number;
    control_conversion: number;
    treatment_conversion: number;
    conversion_uplift_pct: number;
  };
}

export interface ApiEndpointMetrics {
  endpoint: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
}

export interface ApiPerformanceReport {
  system_status: HealthSeverity;
  total_requests: number;
  total_errors: number;
  overall_error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  endpoints: ApiEndpointMetrics[];
}

export interface MonitoringAlert {
  alert_id: string;
  restaurant_id: string;
  alert_type: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  metric_name: string;
  metric_value: number;
  threshold_value: number;
  status: AlertStatus;
  created_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  occurrence_count: number;
  model_version: string | null;
  suggested_action: string;
}

export interface RetrainingRequest {
  request_id: string;
  restaurant_id: string;
  reason: string;
  trigger_type: RetrainingTriggerType;
  trigger_value: string;
  created_at: string;
  completed_at: string | null;
  status: RetrainingStatus;
  result: string | null;
  new_model_version?: string | null;
}

/* =========================================================
   PHASE 5: PRODUCTION, SECURITY, POS INTEGRATION & SCALE
========================================================= */

export type UserRole = 'SUPER_ADMIN' | 'RESTAURANT_ADMIN' | 'MANAGER' | 'STAFF';

export interface AuthUser {
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
  restaurant_id: string;
  restaurant_name: string;
  token: string;
}

export interface AuditLog {
  audit_id: string;
  restaurant_id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export type POSConnectionStatus = 'CONNECTED' | 'DISCONNECTED' | 'SYNCING' | 'ERROR';

export interface POSSyncLog {
  sync_id: string;
  restaurant_id: string;
  provider: string;
  started_at: string;
  completed_at: string | null;
  records_received: number;
  records_inserted: number;
  records_updated: number;
  records_failed: number;
  status: 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'RUNNING';
  error_message?: string | null;
}

export interface POSIntegrationConfig {
  provider: 'square' | 'toast' | 'petpooja' | 'clover' | 'standard_rest';
  api_key_configured: boolean;
  webhook_secret_configured: boolean;
  sync_frequency_minutes: number;
  auto_sync_enabled: boolean;
  last_sync_time?: string;
  connection_status: POSConnectionStatus;
  records_synced_today: number;
}

export interface RestaurantTenant {
  restaurant_id: string;
  name: string;
  currency: string;
  timezone: string;
  is_active: boolean;
  pos_status: POSConnectionStatus;
  total_orders: number;
  data_quality_score: number;
  active_model: string;
  created_at: string;
}

export interface SystemReadinessReport {
  status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE';
  liveness: boolean;
  readiness: boolean;
  database: {
    status: 'HEALTHY' | 'DEGRADED';
    engine: string;
    pool_active: number;
    latency_ms: number;
  };
  model_service: {
    status: 'HEALTHY' | 'DEGRADED';
    active_version: string;
    registry_count: number;
  };
  recommendation_engine: {
    status: 'HEALTHY' | 'DEGRADED';
    fallback_ready: boolean;
    cache_hit_ratio: number;
  };
  pos_adapter: {
    status: 'ONLINE' | 'OFFLINE';
    connection_status: POSConnectionStatus;
    last_sync: string | null;
  };
  background_jobs: {
    status: 'HEALTHY' | 'BUSY';
    active_count: number;
    failed_count: number;
  };
}

export interface BackgroundJobRecord {
  job_id: string;
  restaurant_id: string;
  job_type: 'ML_TRAINING' | 'DRIFT_ANALYSIS' | 'POS_DATA_SYNC' | 'CSV_BULK_IMPORT' | 'DATABASE_BACKUP';
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
  started_at: string;
  completed_at?: string | null;
  progress: number;
  error?: string | null;
  result?: string | null;
}
