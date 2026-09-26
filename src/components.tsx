import React, { useMemo, useState } from 'react';
import { CalendarDays, RotateCw, UtensilsCrossed, Flame, Search, Calculator, Lightbulb, PackageOpen, Sparkles } from 'lucide-react';

export type DateRangeFilter = 'today' | '7days' | '30days' | '90days' | 'all' | 'custom';

export type StockStatus = 'in_stock' | 'low_stock' | 'out_of_stock';

export interface ProductSalesStat {
  product_id: string;
  product_name: string;
  category: string;
  image_emoji: string;
  selling_price: number;
  cost_price: number;
  total_quantity_sold: number;
  transaction_count: number;
  total_revenue: number;
  total_profit: number;
  profit_margin: number;
  current_stock: number;
  stock_status: StockStatus;
}

export interface HistoricalComboCandidate {
  combo_id: string;
  product_a_id: string;
  product_a_name: string;
  product_a_price: number;
  product_a_cost: number;
  product_b_id: string;
  product_b_name: string;
  product_b_price: number;
  product_b_cost: number;
  pair_transaction_count: number;
  total_valid_transactions: number;
  support: number;
  confidence_a_to_b: number;
  confidence_b_to_a: number;
  lift: number;
  regular_sum_price: number;
  combo_cost: number;
  normal_profit: number;
  suggested_combo_price: number;
  customer_savings: number;
  combo_profit: number;
  profit_difference: number;
  combo_margin: number;
  is_candidate_combo: boolean;
  recommendation_mode: string;
  model_version: string | null;
  predicted_future_combo_purchases_7d: number | null;
  estimated_gross_profit_7d: number | null;
  ranking_score: number;
  explanation: string;
}

const money = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

interface DashboardHeaderProps {
  dateFilter: DateRangeFilter;
  setDateFilter: (filter: DateRangeFilter) => void;
  restaurantName: string;
  isLoading: boolean;
  onRefresh: () => void;
  activeSection: string;
  onNavigate: (section: string) => void;
}

const navigation = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'products', label: 'Products' },
  { id: 'combos', label: 'Combos' },
];

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  dateFilter,
  setDateFilter,
  restaurantName,
  isLoading,
  onRefresh,
  activeSection,
  onNavigate,
}) => (
  <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
    <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500 text-slate-950">
          <UtensilsCrossed className="h-5 w-5" />
        </span>
        <div>
          <h1 className="font-bold text-white">Restaurant Combo Intelligence</h1>
          <p className="text-xs text-slate-400">{restaurantName}</p>
        </div>
      </div>

      <nav className="order-3 flex w-full gap-1 sm:order-2 sm:w-auto" aria-label="Dashboard sections">
        {navigation.map(item => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeSection === item.id
                ? 'bg-amber-500/15 text-amber-300'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="order-2 flex items-center gap-2 sm:order-3">
        <label className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2">
          <CalendarDays className="h-4 w-4 text-slate-400" />
          <span className="sr-only">Sales date range</span>
          <select
            value={dateFilter}
            onChange={event => setDateFilter(event.target.value as DateRangeFilter)}
            className="bg-transparent text-sm text-slate-200 outline-none"
          >
            <option value="today">Today</option>
            <option value="7days">Last 7 Days</option>
            <option value="30days">Last 30 Days</option>
            <option value="90days">Last 90 Days</option>
            <option value="custom">Custom Range</option>
          </select>
        </label>
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          aria-label="Refresh sales"
          className="rounded-xl border border-slate-700 bg-slate-900 p-2 text-slate-300 transition-colors hover:bg-slate-800 disabled:opacity-50"
        >
          <RotateCw className={`h-4 w-4 ${isLoading ? 'animate-spin text-amber-400' : ''}`} />
        </button>
      </div>
    </div>
  </header>
);


interface TopSellingProductsProps {
  products: ProductSalesStat[];
}

export const TopSellingProducts: React.FC<TopSellingProductsProps> = ({ products }) => {
  const [search, setSearch] = useState('');
  const visibleProducts = useMemo(() => products
    .filter(product => product.product_name.toLowerCase().includes(search.toLowerCase()))
    .sort((left, right) => right.total_quantity_sold - left.total_quantity_sold), [products, search]);

  return (
    <section id="products" className="scroll-mt-28 space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-white">
            <Flame className="h-5 w-5 text-amber-400" />
            Top Selling Products
          </h2>
          <p className="mt-1 text-sm text-slate-400">Ranked by quantity sold in the selected period</p>
        </div>
        <label className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2">
          <Search className="h-4 w-4 text-slate-500" />
          <span className="sr-only">Search products</span>
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search products"
            className="w-36 bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-500"
          />
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase text-slate-500">
            <tr>
              <th className="py-3 pr-4 font-medium">Product</th>
              <th className="px-4 py-3 text-right font-medium">Quantity Sold</th>
              <th className="px-4 py-3 text-right font-medium">Orders</th>
              <th className="px-4 py-3 text-right font-medium">Revenue</th>
              <th className="py-3 pl-4 text-right font-medium">Profit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {visibleProducts.length === 0 ? (
              <tr><td colSpan={5} className="py-8 text-center text-slate-500">No product sales found for this period.</td></tr>
            ) : visibleProducts.map((product, index) => (
              <tr key={product.product_id}>
                <td className="py-3 pr-4">
                  <span className="mr-3 text-xs text-slate-500">#{index + 1}</span>
                  <span className="font-medium text-white">{product.product_name}</span>
                </td>
                <td className="px-4 py-3 text-right font-semibold text-white">{product.total_quantity_sold.toLocaleString()}</td>
                <td className="px-4 py-3 text-right text-slate-300">{product.transaction_count.toLocaleString()}</td>
                <td className="px-4 py-3 text-right text-slate-300">{money(product.total_revenue)}</td>
                <td className="py-3 pl-4 text-right font-medium text-emerald-400">{money(product.total_profit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};


interface ComboIntelligenceDashboardProps {
  combos: HistoricalComboCandidate[];
  isLoading: boolean;
}

const ComboCard: React.FC<{ combo: HistoricalComboCandidate }> = ({ combo }) => {
  const [price, setPrice] = useState(combo.suggested_combo_price);
  const values = useMemo(() => {
    const normalProfit =
      (combo.product_a_price - combo.product_a_cost) +
      (combo.product_b_price - combo.product_b_cost);
    const comboProfit = price - combo.combo_cost;
    return {
      customerSaving: combo.regular_sum_price - price,
      normalProfit,
      comboProfit,
      profitDifference: comboProfit - normalProfit,
    };
  }, [combo, price]);

  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-white">{combo.product_a_name} + {combo.product_b_name}</h3>
          <p className="mt-1 text-xs text-slate-400">
            {combo.recommendation_mode}
            {combo.model_version ? ' · ranked from restaurant sales history' : ' · based on observed sales rules'}
          </p>
        </div>
        <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
          {money(values.comboProfit)} estimated profit / combo
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Metric label="Bought Together" value={combo.pair_transaction_count.toLocaleString()} />
        <Metric label="Support" value={`${(combo.support * 100).toFixed(1)}%`} />
        <Metric label={`Confidence: ${combo.product_a_name} → ${combo.product_b_name}`} value={`${(combo.confidence_a_to_b * 100).toFixed(1)}%`} />
        <Metric label={`Confidence: ${combo.product_b_name} → ${combo.product_a_name}`} value={`${(combo.confidence_b_to_a * 100).toFixed(1)}%`} />
        <Metric label="Lift" value={`${combo.lift.toFixed(2)}×`} />
      </div>

      <section className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        <h4 className="flex items-center gap-2 text-sm font-semibold text-white">
          <Lightbulb className="h-4 w-4 text-amber-400" />
          Why this combo?
        </h4>
        <p className="mt-2 text-sm leading-6 text-slate-300">{combo.explanation}</p>
      </section>

      <section className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        <h4 className="flex items-center gap-2 text-sm font-semibold text-white">
          <Calculator className="h-4 w-4 text-amber-400" />
          Combo Profit Calculator
        </h4>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <label className="text-sm text-slate-300">
            Combo price
            <span className="ml-3 inline-flex items-center rounded-lg border border-slate-700 bg-slate-900 px-2">
              <span className="text-slate-500">₹</span>
              <input
                aria-label={`Combo price for ${combo.product_a_name} and ${combo.product_b_name}`}
                type="number"
                min="0"
                step="0.01"
                value={Number.isFinite(price) ? price : ''}
                onChange={event => setPrice(Math.max(0, Number(event.target.value) || 0))}
                className="w-24 bg-transparent px-2 py-2 text-right text-sm text-white outline-none"
              />
            </span>
          </label>
          <p className="text-xs text-slate-500">Historical estimate only; actual results may vary.</p>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <MoneyMetric label="Normal Price" value={combo.regular_sum_price} />
          <MoneyMetric label="Customer Saving" value={values.customerSaving} />
          <MoneyMetric label="Combo Cost" value={combo.combo_cost} />
          <MoneyMetric label="Normal Profit" value={values.normalProfit} />
          <MoneyMetric label="Estimated Combo Profit" value={values.comboProfit} emphasis />
          <MoneyMetric label="Profit Difference" value={values.profitDifference} />
        </dl>
      </section>
    </article>
  );
};

const Metric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-xl bg-slate-950/70 p-3">
    <dt className="text-xs text-slate-500">{label}</dt>
    <dd className="mt-1 font-semibold text-slate-100">{value}</dd>
  </div>
);

const MoneyMetric: React.FC<{ label: string; value: number; emphasis?: boolean }> = ({
  label,
  value,
  emphasis = false,
}) => (
  <div className="rounded-xl bg-slate-900 p-3">
    <dt className="text-xs text-slate-500">{label}</dt>
    <dd className={`mt-1 font-semibold ${emphasis ? 'text-emerald-400' : 'text-slate-100'}`}>{money(value)}</dd>
  </div>
);

export const ComboIntelligenceDashboard: React.FC<ComboIntelligenceDashboardProps> = ({
  combos,
  isLoading,
}) => {
  const recommended = combos.filter(combo => combo.is_candidate_combo);

  return (
    <section id="combos" className="scroll-mt-28 space-y-4">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
          <Sparkles className="h-5 w-5 text-amber-400" />
          Recommended Combos
        </h2>
        <p className="mt-1 text-sm text-slate-400">Pairs are found in actual restaurant transactions, then ranked by the trained model when available.</p>
      </div>
      {isLoading && combos.length === 0 ? (
        <p className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-400">Loading sales and combos…</p>
      ) : recommended.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center">
          <PackageOpen className="mx-auto mb-3 h-8 w-8 text-slate-500" />
          <h3 className="font-semibold text-white">No combos meet the sales and profit rules</h3>
          <p className="mt-1 text-sm text-slate-400">Try a wider date range or wait for more co-purchases to accumulate.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {recommended.map(combo => <ComboCard key={combo.combo_id} combo={combo} />)}
        </div>
      )}
    </section>
  );
};
