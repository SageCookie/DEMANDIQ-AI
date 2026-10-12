import React, { useState } from "react";
import { Plus, Search, Package, ArrowUpRight, DollarSign, Clock, Check, X } from "lucide-react";
import { Product } from "../types";
import { api } from "../lib/api";

interface ProductsPageProps {
  products: Product[];
  onSelectProduct: (productId: string) => void;
  onRefresh: () => void;
}

export const ProductsPage: React.FC<ProductsPageProps> = ({ products, onSelectProduct, onRefresh }) => {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("ALL");
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({
    product_code: "",
    product_name: "",
    category: "Consumer Electronics",
    unit_price: 49.99,
    lead_time_days: 7,
    initial_inventory: 100,
  });
  const [submitting, setSubmitting] = useState(false);

  const categories = Array.from(new Set(products.map((p) => p.category)));

  const filtered = products.filter((p) => {
    const matchCat = category === "ALL" || p.category === category;
    const matchSearch =
      p.product_name.toLowerCase().includes(search.toLowerCase()) ||
      p.product_code.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createProduct(formData);
      setShowAddModal(false);
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to create product");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Products Catalog & SKUs</h2>
          <p className="text-xs text-slate-500">Manage active catalog items, supplier lead times, and inventory levels.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search SKU or name..."
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800"
            />
          </div>

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium text-slate-700"
          >
            <option value="ALL">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <button onClick={() => setShowAddModal(true)} className="btn-primary">
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </button>
        </div>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((prod) => (
          <div
            key={prod.id}
            onClick={() => onSelectProduct(prod.product_code)}
            className="card p-5 space-y-4 hover:border-slate-300 hover:shadow-md cursor-pointer transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="space-y-0.5">
                <span className="text-[10px] font-mono font-bold text-blue-600 uppercase bg-blue-50 px-2 py-0.5 rounded-md">
                  {prod.product_code}
                </span>
                <h3 className="font-extrabold text-sm text-slate-900 mt-1">{prod.product_name}</h3>
                <p className="text-xs text-slate-500">{prod.category}</p>
              </div>
              <span className="badge-green text-[10px] font-bold">Active</span>
            </div>

            <div className="grid grid-cols-3 gap-2 py-2 border-y border-slate-100 text-xs">
              <div>
                <span className="text-slate-600 block text-[10px] uppercase font-bold">Price</span>
                <span className="font-bold text-slate-900">${prod.unit_price.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-slate-600 block text-[10px] uppercase font-bold">Lead Time</span>
                <span className="font-bold text-slate-900">{prod.lead_time_days} days</span>
              </div>
              <div>
                <span className="text-slate-600 block text-[10px] uppercase font-bold">In Stock</span>
                <span className="font-bold text-blue-600">{prod.current_inventory} units</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-600">
              <span>On Order: {prod.on_order_quantity} units</span>
              <span className="font-bold text-blue-600 hover:underline flex items-center gap-1">
                Inspect SKU <ArrowUpRight className="w-3.5 h-3.5" />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Add Product Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="card p-6 max-w-md w-full bg-white shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="font-extrabold text-base text-slate-900">Add New Catalog Product</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">SKU / Product Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. P013"
                  value={formData.product_code}
                  onChange={(e) => setFormData({ ...formData, product_code: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Product Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. UltraSensor IoT Gateway"
                  value={formData.product_name}
                  onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                >
                  <option value="Consumer Electronics">Consumer Electronics</option>
                  <option value="Industrial">Industrial</option>
                  <option value="Apparel & Gear">Apparel & Gear</option>
                  <option value="Home & Office">Home & Office</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Unit Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.unit_price}
                    onChange={(e) => setFormData({ ...formData, unit_price: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Lead Time (Days)</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.lead_time_days}
                    onChange={(e) => setFormData({ ...formData, lead_time_days: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Initial Stock Inventory</label>
                <input
                  type="number"
                  min="0"
                  required
                  value={formData.initial_inventory}
                  onChange={(e) => setFormData({ ...formData, initial_inventory: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="pt-3 flex gap-2">
                <button type="submit" disabled={submitting} className="flex-1 btn-primary">
                  {submitting ? "Saving..." : "Create Product"}
                </button>
                <button type="button" onClick={() => setShowAddModal(false)} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
