# products_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean,
    GraphQLArgument
)
from repository import (
    create_category, get_category, get_categories,
    create_product, get_product, get_products_by_ids,
    add_product_attribute, add_product_image,
    check_stock, reserve_stock, release_stock,
    update_stock_admin, get_low_stock_products, search_products
)

# ========================
# TYPES
# ========================

CategoryType = GraphQLObjectType('Category', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
    'parent_id': GraphQLField(GraphQLInt),
    'description': GraphQLField(GraphQLString),
    'is_active': GraphQLField(GraphQLBoolean),
    'created_at': GraphQLField(GraphQLString),
    'updated_at': GraphQLField(GraphQLString),
})

AttributeType = GraphQLObjectType('Attribute', {
    'attribute_name': GraphQLField(GraphQLString),
    'attribute_value': GraphQLField(GraphQLString),
})

ImageType = GraphQLObjectType('Image', {
    'image_url': GraphQLField(GraphQLString),
    'alt_text': GraphQLField(GraphQLString),
    'is_main': GraphQLField(GraphQLBoolean),
})

StockCheckResultType = GraphQLObjectType('StockCheckResult', {
    'product_id': GraphQLField(GraphQLInt),
    'available': GraphQLField(GraphQLInt),
    'reserved': GraphQLField(GraphQLInt),
    'free_stock': GraphQLField(GraphQLInt),
    'requested': GraphQLField(GraphQLInt),
    'in_stock': GraphQLField(GraphQLBoolean),
    'message': GraphQLField(GraphQLString),
})

LowStockProductType = GraphQLObjectType('LowStockProduct', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'sku': GraphQLField(GraphQLString),
    'quantity': GraphQLField(GraphQLInt),
    'reserved_quantity': GraphQLField(GraphQLInt),
    'free_stock': GraphQLField(GraphQLInt, resolve=lambda p, _: p['quantity'] - p['reserved_quantity']),
})

ProductType = GraphQLObjectType('Product', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
    'description': GraphQLField(GraphQLString),
    'short_description': GraphQLField(GraphQLString),
    'price': GraphQLField(GraphQLFloat),
    'old_price': GraphQLField(GraphQLFloat),
    'sku': GraphQLField(GraphQLString),
    'category_id': GraphQLField(GraphQLInt),
    'category_name': GraphQLField(GraphQLString),
    'brand': GraphQLField(GraphQLString),
    'is_active': GraphQLField(GraphQLBoolean),
    'stock_available': GraphQLField(GraphQLInt),
    'reserved_quantity': GraphQLField(GraphQLInt),
    'free_stock': GraphQLField(GraphQLInt, resolve=lambda p, _: p['stock_available'] - p['reserved_quantity']),
    'weight_kg': GraphQLField(GraphQLFloat),
    'dimensions': GraphQLField(GraphQLString),
    'warranty_months': GraphQLField(GraphQLInt),
    'created_at': GraphQLField(GraphQLString),
    'updated_at': GraphQLField(GraphQLString),
    'attributes': GraphQLField(GraphQLList(AttributeType)),
    'images': GraphQLField(GraphQLList(ImageType)),
})

# ========================
# INPUT TYPES
# ========================

CreateCategoryInput = GraphQLInputObjectType('CreateCategoryInput', {
    'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'slug': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'parent_id': GraphQLInputField(GraphQLInt),
    'description': GraphQLInputField(GraphQLString),
})

CreateProductInput = GraphQLInputObjectType('CreateProductInput', {
    'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'slug': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'price': GraphQLInputField(GraphQLNonNull(GraphQLFloat)),
    'category_id': GraphQLInputField(GraphQLInt),
    'description': GraphQLInputField(GraphQLString),
    'short_description': GraphQLInputField(GraphQLString),
    'old_price': GraphQLInputField(GraphQLFloat),
    'sku': GraphQLInputField(GraphQLString),
    'brand': GraphQLInputField(GraphQLString),
    'stock_quantity': GraphQLInputField(GraphQLInt, default_value=0),
    'weight_kg': GraphQLInputField(GraphQLFloat),
    'dimensions': GraphQLInputField(GraphQLString),
    'warranty_months': GraphQLInputField(GraphQLInt, default_value=0),
})

AddAttributeInput = GraphQLInputObjectType('AddAttributeInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'value': GraphQLInputField(GraphQLNonNull(GraphQLString)),
})

AddImageInput = GraphQLInputObjectType('AddImageInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'image_url': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'alt_text': GraphQLInputField(GraphQLString),
    'is_main': GraphQLInputField(GraphQLBoolean),
    'sort_order': GraphQLInputField(GraphQLInt),
})

StockItemInput = GraphQLInputObjectType('StockItemInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'quantity': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
})

StockUpdateInput = GraphQLInputObjectType('StockUpdateInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'quantity': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
})

SearchInput = GraphQLInputObjectType('SearchInput', {
    'query': GraphQLInputField(GraphQLString),
    'category_id': GraphQLInputField(GraphQLInt),
    'min_price': GraphQLInputField(GraphQLFloat),
    'max_price': GraphQLInputField(GraphQLFloat),
    'in_stock_only': GraphQLInputField(GraphQLBoolean),
    'limit': GraphQLInputField(GraphQLInt),
    'offset': GraphQLInputField(GraphQLInt),
})

# ========================
# QUERY
# ========================

Query = GraphQLObjectType('Query', {
    'categories': GraphQLField(
        GraphQLList(CategoryType),
        resolve=lambda *_: get_categories()
    ),
    'category': GraphQLField(
        CategoryType,
        args={'id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, id: get_category(id)
    ),
    'product': GraphQLField(
        ProductType,
        args={'id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, id: get_product(id)
    ),
    'productsByIds': GraphQLField(
        GraphQLList(ProductType),
        args={'ids': GraphQLNonNull(GraphQLList(GraphQLNonNull(GraphQLInt)))},
        resolve=lambda _, info, ids: get_products_by_ids(ids)
    ),
    'checkStock': GraphQLField(
        GraphQLList(StockCheckResultType),
        args={'items': GraphQLNonNull(GraphQLList(GraphQLNonNull(StockItemInput)))},
        resolve=lambda _, info, items: check_stock(items)
    ),
    'lowStock': GraphQLField(
        GraphQLList(LowStockProductType),
        args={'threshold': GraphQLInt},
        resolve=lambda _, info, threshold=10: get_low_stock_products(threshold)
    ),
    'search': GraphQLField(
        GraphQLList(ProductType),
        args={'input': SearchInput},
        resolve=lambda _, info, input={}: search_products(**input)
    ),
})

# ========================
# MUTATION
# ========================

Mutation = GraphQLObjectType('Mutation', {
    # === CATEGORY ===
    'createCategory': GraphQLField(
        CategoryType,
        args={'input': GraphQLNonNull(CreateCategoryInput)},
        resolve=lambda _, info, input: create_category(**input)
    ),

    # === PRODUCT ===
    'createProduct': GraphQLField(
        ProductType,
        args={'input': GraphQLNonNull(CreateProductInput)},
        resolve=lambda _, info, input: create_product(**input)
    ),

    # === ATTRIBUTE & IMAGE ===
    'addAttribute': GraphQLField(
        GraphQLBoolean,
        args={'input': GraphQLNonNull(AddAttributeInput)},
        resolve=lambda _, info, input: add_product_attribute(**input)
    ),
    'addImage': GraphQLField(
        GraphQLBoolean,
        args={'input': GraphQLNonNull(AddImageInput)},
        resolve=lambda _, info, input: add_product_image(**input)
    ),

    # === STOCK ===
    'reserveStock': GraphQLField(
        GraphQLBoolean,
        args={'items': GraphQLNonNull(GraphQLList(GraphQLNonNull(StockItemInput)))},
        resolve=lambda _, info, items: reserve_stock(items)
    ),
    'releaseStock': GraphQLField(
        GraphQLBoolean,
        args={'items': GraphQLNonNull(GraphQLList(GraphQLNonNull(StockItemInput)))},
        resolve=lambda _, info, items: release_stock(items)
    ),
    'updateStock': GraphQLField(
        GraphQLBoolean,
        args={'input': GraphQLNonNull(StockUpdateInput)},
        resolve=lambda _, info, input: update_stock_admin(**input)
    ),
})

# ========================
# SCHEMA
# ========================

schema = GraphQLSchema(query=Query, mutation=Mutation)