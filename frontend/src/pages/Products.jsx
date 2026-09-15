import { useState, useMemo } from "react";
import { Search, Plus, ChevronDown } from "lucide-react";
import ProductTable from "../components/ProductTable";
import Button from "../components/Button";
import AddProductModal from "../components/AddProductModal";
import { mockProducts, categories } from "../data/mockProducts";

export default function Products({ shop }) {
  const [products, setProducts] = useState(mockProducts);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [showModal, setShowModal] = useState(false);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const matchesSearch = p.name
        .toLowerCase()
        .includes(search.toLowerCase());

      const matchesCategory =
        category === "All" || p.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [products, search, category]);

  const handleAdd = (product) => {
    setProducts((prev) => [
      { id: Date.now(), ...product },
      ...prev,
    ]);

    setShowModal(false);
  };

  return (
    <div>
      <div className="flex items-start justify-between">
          <div>
            <h1 className="text-[24px] font-semibold text-ink">
              Products
            </h1>

            <p className="mt-1 text-[14px] text-ink/60">
              Manage the products and stock for your shop
            </p>
          </div>

          <Button
            variant="accent"
            icon={Plus}
            onClick={() => setShowModal(true)}
          >
            Add Product
          </Button>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <div className="flex min-w-[240px] flex-1 items-center gap-2 rounded-control border border-ink/15 bg-white px-3 py-2.5">
            <Search size={16} className="text-ink/40" />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products"
              className="w-full bg-transparent text-[14px] text-ink placeholder:text-ink/35 focus:outline-none"
            />
          </div>

          <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="appearance-none bg-transparent pr-6 text-[14px] text-ink focus:outline-none"
            >
              <option value="All">All Categories</option>

              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            <ChevronDown
              size={15}
              className="pointer-events-none absolute right-3 text-ink/40"
            />
          </div>
        </div>

        <div className="mt-5">
          <ProductTable products={filtered} />
        </div>

      {showModal && (
        <AddProductModal
          onClose={() => setShowModal(false)}
          onAdd={handleAdd}
        />
      )}
    </div>
  );
}