from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.routes import adjust_inventory, create_purchase_order
from src.api.schemas import InventoryAdjustmentRequest, PurchaseOrderCreate
from src.database.models import Base, Inventory, InventoryTransaction, Organization, Product, PurchaseOrder


def test_adjustment_and_purchase_order_are_persisted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    organization = Organization(name="Test Workspace", slug="test-workspace")
    session.add(organization)
    session.flush()
    user = SimpleNamespace(role="INVENTORY_MANAGER", username="planner", organization_id=organization.id)
    product = Product(organization_id=organization.id, product_code="TEST-SKU", product_name="Workflow Widget", category="Test", unit_price=12.0, lead_time_days=5)
    session.add(product)
    session.flush()
    session.add(Inventory(product_id=product.id, quantity_available=10, quantity_reserved=0, quantity_on_order=0))
    session.commit()

    result = adjust_inventory("TEST-SKU", InventoryAdjustmentRequest(quantity_delta=5, reason="cycle count"), user, session)
    assert result["quantity_before"] == 10
    assert result["quantity_after"] == 15
    assert session.query(InventoryTransaction).one().created_by == "planner"

    order = create_purchase_order(PurchaseOrderCreate(product_id="TEST-SKU", quantity=20), user, session)
    assert order["status"] == "DRAFT"
    assert order["order_number"].startswith("PO-")
    assert session.query(PurchaseOrder).one().quantity == 20
    assert session.query(Inventory).one().quantity_on_order == 20
