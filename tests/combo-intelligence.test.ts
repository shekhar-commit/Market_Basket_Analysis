import assert from 'node:assert/strict';
import test from 'node:test';
import { analyzeRestaurantSales } from '../server.ts';
import type { ComboAnalysisProduct } from '../server.ts';
import type { InventoryItem, Transaction } from '../src/App.tsx';

const product = (
  id: string,
  cost: number | null = 20,
  restaurantId = 'R001',
): ComboAnalysisProduct => ({
  product_id: id,
  restaurant_id: restaurantId,
  product_name: `Product ${id}`,
  category: 'Test',
  image_emoji: '•',
  selling_price: 50,
  cost_price: cost,
  is_active: true,
});

const item = (transactionId: string, productId: string, price = 50) => ({
  transaction_id: transactionId,
  product_id: productId,
  product_name: `Product ${productId}`,
  quantity: 1,
  unit_price: price,
  discount_amount: 0,
  net_price: price,
  total_price: price,
});

const order = (
  id: string,
  productIds: string[],
  restaurantId = 'R001',
  timestamp = '2026-09-24T12:00:00.000Z',
): Transaction => ({
  transaction_id: id,
  restaurant_id: restaurantId,
  transaction_date: timestamp.slice(0, 10),
  transaction_time: '12:00',
  total_amount: productIds.length * 50,
  discount_amount: 0,
  order_status: 'completed',
  payment_status: 'paid',
  channel: 'dine_in',
  timestamp,
  created_at: timestamp,
  items: productIds.map(productId => item(id, productId)),
});

const run = (
  products: ComboAnalysisProduct[],
  transactions: Transaction[],
  inventory: InventoryItem[] = [],
  options: Parameters<typeof analyzeRestaurantSales>[4] = {},
) => analyzeRestaurantSales('R001', products, inventory, transactions, {
  minSupport: 0,
  minConfidence: 0,
  minLift: 0,
  ...options,
});

test('calculates pair support, directional confidence, lift, and combo profit', () => {
  const summary = run(
    [product('A', 50), product('B', 20), product('C')],
    [
      order('O1', ['A', 'B']),
      order('O2', ['A', 'B']),
      order('O3', ['A']),
      order('O4', ['B']),
      order('O5', ['C']),
    ],
    [],
    { comboDiscountPercentage: 0.5, minProfit: 20, minLift: 1 },
  );

  const combo = summary.suggested_combos.find(candidate =>
    candidate.products.length === 2 &&
    candidate.products.some(product => product.product_id === 'A') &&
    candidate.products.some(product => product.product_id === 'B'),
  );
  assert.ok(combo);
  assert.equal(combo.orders_together, 2);
  assert.equal(combo.support, 0.4);
  assert.equal(combo.confidence, 0.6667);
  assert.equal(combo.lift, 1.1111);
  assert.equal(combo.individual_price, 100);
  assert.equal(combo.combo_price, 90);
  assert.equal(combo.total_cost, 70);
  assert.equal(combo.profit, 20);
  assert.equal(combo.profit_margin_percentage, 22.22);
  assert.equal(combo.combo_discount_percentage, 10);
  assert.equal(combo.maximum_safe_discount_percentage, 10);
  assert.equal(combo.confidence_antecedent_product_ids.length, 1);
  assert.ok(combo.confidence_consequent_product_id);
});

test('generates actual three-product combinations without repeated products', () => {
  const summary = run(
    [product('A'), product('B'), product('C')],
    [order('O1', ['A', 'B', 'C']), order('O2', ['A', 'B', 'C'])],
  );

  const triple = summary.suggested_combos.find(combo => combo.products.length === 3);
  assert.ok(triple);
  assert.equal(triple.support, 1);
  assert.equal(triple.confidence, 1);
  assert.equal(triple.lift, 1);
  assert.ok(summary.suggested_combos.every(combo =>
    new Set(combo.products.map(product => product.product_id)).size === combo.products.length,
  ));
});

test('does not recommend stockouts or combos below the minimum profit', () => {
  const products = [product('A', 45), product('B', 45)];
  const transactions = [order('O1', ['A', 'B']), order('O2', ['A', 'B'])];
  const stockout: InventoryItem = {
    product_id: 'B',
    product_name: 'Product B',
    current_stock: 0,
    minimum_stock: 1,
    reorder_level: 1,
    is_available: false,
    last_updated: '2026-09-24T12:00:00.000Z',
  };

  const unavailable = run(products, transactions, [stockout]);
  assert.equal(unavailable.suggested_combos.length, 0);
  assert.equal(unavailable.summary.combo_candidates, 1);

  const insufficientProfit = run(products, transactions, [], { minProfit: 11 });
  assert.equal(insufficientProfit.suggested_combos.length, 0);

  const filteredBySupport = run(products, [...transactions, order('O3', ['A'])], [], { minSupport: 0.8 });
  assert.equal(filteredBySupport.summary.combo_candidates, 0);
});

test('keeps basket evidence but marks profit unavailable when cost data is missing', () => {
  const summary = run(
    [product('A', null), product('B', 20)],
    [order('O1', ['A', 'B']), order('O2', ['A', 'B'])],
  );

  assert.equal(summary.suggested_combos.length, 0);
  assert.equal(summary.summary.combo_candidates, 1);
  assert.equal(summary.recent_popular_combos[0].profit, null);
  assert.match(summary.recent_popular_combos[0].profit_unavailable_reason ?? '', /cost data is missing/);
  assert.equal(summary.recent_popular_combos[0].is_recommended, false);
});

test('does not create recommendations for inactive products or zero selling prices', () => {
  const inactiveProducts = [product('A'), { ...product('B'), is_active: false }];
  const inactive = run(inactiveProducts, [order('O1', ['A', 'B']), order('O2', ['A', 'B'])]);
  assert.equal(inactive.summary.combo_candidates, 0);

  const invalidPrice = run(
    [{ ...product('A'), selling_price: 0 }, product('B')],
    [order('O1', ['A', 'B']), order('O2', ['A', 'B'])],
  );
  assert.equal(invalidPrice.suggested_combos.length, 0);
  assert.equal(invalidPrice.combo_candidates[0].profit, null);
});

test('isolates restaurant data and validates sales rows', () => {
  const summary = run(
    [product('A'), product('B')],
    [
      order('R1', ['A', 'B']),
      order('R2', ['A', 'B'], 'R002'),
      {
        ...order('INVALID', ['A']),
        items: [{ ...item('INVALID', 'A'), quantity: 0 }],
      },
    ],
  );

  assert.equal(summary.summary.orders_analyzed, 1);
  assert.equal(summary.summary.invalid_rows, 1);
  assert.equal(summary.summary.products_analyzed, 2);
  assert.equal(summary.suggested_combos[0].orders_together, 1);
});

test('returns explicit empty-sales state and recent sales quantities', () => {
  const empty = run([product('A')], []);
  assert.equal(empty.message, 'No sales data available for this period.');
  assert.deepEqual(empty.top_selling_products, []);

  const summary = run(
    [product('A'), product('B')],
    [
      order('OLD', ['A', 'B'], 'R001', '2026-08-01T12:00:00.000Z'),
      order('RECENT', ['A', 'B'], 'R001', '2026-09-24T12:00:00.000Z'),
    ],
    [],
    { allTime: true },
  );
  const popular = summary.top_selling_products.find(sales => sales.product_id === 'A');
  assert.equal(popular?.total_quantity_sold, 2);
  assert.equal(popular?.recent_quantity_sold, 1);
  assert.equal(summary.recent_popular_combos[0].recent_orders_together_7d, 1);
});
