# cart_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean
)
from repository import (
    add_to_cart, get_cart, update_cart_item, remove_from_cart,
    prepare_checkout, generate_session_id, merge_guest_cart
)

# ========================
# TYPES
# ========================
CartItemType = GraphQLObjectType('CartItem', {
    'id': GraphQLField(GraphQLInt),
    'product_id': GraphQLField(GraphQLInt),
    'product_name': GraphQLField(GraphQLString),
    'variant_id': GraphQLField(GraphQLInt),
    'quantity': GraphQLField(GraphQLInt),
    'price': GraphQLField(GraphQLFloat),
    'total': GraphQLField(GraphQLFloat, resolve=lambda obj, _: obj['price'] * obj['quantity']),
})

CartSummaryType = GraphQLObjectType('CartSummary', {
    'items_count': GraphQLField(GraphQLInt),
    'total_quantity': GraphQLField(GraphQLInt),
    'total_price': GraphQLField(GraphQLFloat),
})

CartType = GraphQLObjectType('Cart', {
    'cart_id': GraphQLField(GraphQLInt),
    'items': GraphQLField(GraphQLList(CartItemType)),
    'summary': GraphQLField(CartSummaryType),
    'is_guest': GraphQLField(GraphQLBoolean),
})

CheckoutResultType = GraphQLObjectType('CheckoutResult', {
    'cart_id': GraphQLField(GraphQLInt),
    'total_amount': GraphQLField(GraphQLFloat),
    'currency': GraphQLField(GraphQLString),
    'items': GraphQLField(GraphQLList(CartItemType)),
    'status': GraphQLField(GraphQLString),
})

# ========================
# INPUTS
# ========================
AddToCartInput = GraphQLInputObjectType('AddToCartInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'variant_id': GraphQLInputField(GraphQLInt),
    'quantity': GraphQLInputField(GraphQLInt, default_value=1),
})

UpdateCartItemInput = GraphQLInputObjectType('UpdateCartItemInput', {
    'item_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'quantity': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
})

# ========================
# QUERY
# ========================
Query = GraphQLObjectType('Query', {
    'cart': GraphQLField(
        CartType,
        args={
            'user_id': GraphQLInt,
            'session_id': GraphQLNonNull(GraphQLString)
        },
        resolve=lambda _, info, user_id=None, session_id=None: get_cart(user_id, session_id)
    ),
    'generateSession': GraphQLField(
        GraphQLString,
        resolve=lambda *_: generate_session_id()
    ),
})

# ========================
# MUTATION
# ========================
Mutation = GraphQLObjectType('Mutation', {
    'addToCart': GraphQLField(
        CartType,
        args={
            'user_id': GraphQLInt,
            'session_id': GraphQLNonNull(GraphQLString),
            'input': GraphQLNonNull(AddToCartInput)
        },
        resolve=lambda _, info, user_id=None, session_id=None, input=None: add_to_cart(user_id, session_id, **input)
    ),
    'updateCartItem': GraphQLField(
        CartType,
        args={'input': GraphQLNonNull(UpdateCartItemInput)},
        resolve=lambda _, info, input=None: update_cart_item(**input)
    ),
    'removeFromCart': GraphQLField(
        CartType,
        args={'item_id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, item_id: remove_from_cart(item_id)
    ),
    'mergeGuestCart': GraphQLField(
        CartType,
        args={
            'guest_session_id': GraphQLNonNull(GraphQLString),
            'user_id': GraphQLNonNull(GraphQLInt)
        },
        resolve=lambda _, info, guest_session_id, user_id: merge_guest_cart(guest_session_id, user_id)
    ),
    'prepareCheckout': GraphQLField(
        CheckoutResultType,
        args={'cart_id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, cart_id: prepare_checkout(cart_id)
    ),
})

# ========================
# SCHEMA
# ========================
schema = GraphQLSchema(query=Query, mutation=Mutation)