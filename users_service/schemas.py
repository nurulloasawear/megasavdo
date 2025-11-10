from graphql import *
from repository import get_users,get_user,create_user

UserType = GraphQLObjectType('User', {
    'id': GraphQLField(GraphQLInt),
    'username': GraphQLField(GraphQLString),
    'name': GraphQLField(GraphQLString),
    'role': GraphQLField(GraphQLString)
})

CreateUserInput = GraphQLInputObjectType('CreateUserInput', {
    'username': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'role': GraphQLInputField(GraphQLString),
    'phone_number': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'password': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'email': GraphQLInputField(GraphQLNonNull(GraphQLString))
})
Query = GraphQLObjectType('Query', {
    'users':GraphQLField(GraphQLList(UserType),
        resolve=lambda *_: get_users()),
    'user':GraphQLField(UserType,
        args={'id':GraphQLArgument(GraphQLNonNull(GraphQLInt))})})
Mutation = GraphQLObjectType('Mutation', {
    'createUser':GraphQLField(UserType,
        args={'input':GraphQLArgument(GraphQLNonNull(CreateUserInput))},
        resolve=lambda _, info, input: create_user(input))
})
schema  = GraphQLSchema(query=Query, mutation=Mutation)