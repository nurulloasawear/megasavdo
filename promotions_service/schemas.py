# promotions_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean
)
from repository import (
    validate_promo_code, get_flash_sale_discount,
    add_points, validate_gift_card
)

# TYPES
PromoResultType = GraphQLObjectType('PromoResult', {
    'promo_id': GraphQLField(GraphQLInt),
    'code': GraphQLField(GraphQLString),
    'discount': GraphQLField(GraphQLFloat),
    'new_total': GraphQLField(GraphQLFloat),
})

GiftCardResultType = GraphQLObjectType('GiftCardResult', {
    'card_id': GraphQLField(GraphQLInt),
    'balance': GraphQLField(GraphQLFloat),
    'use_amount': GraphQLField(GraphQLFloat),
})

# INPUTS
CartItemInput = GraphQLInputObjectType('CartItemInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'quantity': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'price': GraphQLInputField(GraphQLNonNull(GraphQLFloat)),
})

# MUTATION
Mutation = GraphQLObjectType('Mutation', {
    'validatePromo': GraphQLField(
        PromoResultType,
        args={
            'code': GraphQLNonNull(GraphQLString),
            'cart_items': GraphQLNonNull(GraphQLList(CartItemInput)),
            'user_id': GraphQLInt
        },
        resolve=lambda _, i, code, cart_items, user_id=None: validate_promo_code(code, cart_items, user_id)
    ),
    'validateGiftCard': GraphQLField(
        GiftCardResultType,
        args={
            'code': GraphQLNonNull(GraphQLString),
            'amount': GraphQLNonNull(GraphQLFloat)
        },
        resolve=lambda _, i, code, amount: validate_gift_card(code, amount)
    ),
})

schema = GraphQLSchema(mutation=Mutation)