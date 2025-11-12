# blog_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLInputObjectType,
    GraphQLInputField, GraphQLBoolean
)
from repository import (
    get_categories, create_category, get_tags,
    create_post, get_post_by_slug, get_posts, search_posts
)

# TYPES
CategoryType = GraphQLObjectType('Category', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
})

TagType = GraphQLObjectType('Tag', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
})

PostType = GraphQLObjectType('Post', {
    'id': GraphQLField(GraphQLInt),
    'title': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
    'content': GraphQLField(GraphQLString),
    'excerpt': GraphQLField(GraphQLString),
    'image_url': GraphQLField(GraphQLString),
    'published_at': GraphQLField(GraphQLString),
    'category_name': GraphQLField(GraphQLString),
    'username': GraphQLField(GraphQLString),
    'view_count': GraphQLField(GraphQLInt),
    'tags': GraphQLField(GraphQLList(TagType)),
})

PostPreviewType = GraphQLObjectType('PostPreview', {
    'id': GraphQLField(GraphQLInt),
    'title': GraphQLField(GraphQLString),
    'slug': GraphQLField(GraphQLString),
    'excerpt': GraphQLField(GraphQLString),
    'image_url': GraphQLField(GraphQLString),
    'published_at': GraphQLField(GraphQLString),
    'category_name': GraphQLField(GraphQLString),
    'username': GraphQLField(GraphQLString),
})

# INPUTS
PostInput = GraphQLInputObjectType('PostInput', {
    'title': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'slug': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'content': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'excerpt': GraphQLInputField(GraphQLString),
    'image_url': GraphQLInputField(GraphQLString),
    'author_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'category_id': GraphQLInputField(GraphQLInt),
    'is_published': GraphQLInputField(GraphQLBoolean),
    'published_at': GraphQLInputField(GraphQLString),
    'meta_title': GraphQLInputField(GraphQLString),
    'meta_description': GraphQLInputField(GraphQLString),
    'tag_ids': GraphQLInputField(GraphQLList(GraphQLInt)),
})

# QUERY
Query = GraphQLObjectType('Query', {
    'categories': GraphQLField(GraphQLList(CategoryType), resolve=lambda *_: get_categories()),
    'tags': GraphQLField(GraphQLList(TagType), resolve=lambda *_: get_tags()),
    'post': GraphQLField(PostType, args={'slug': GraphQLNonNull(GraphQLString)}, resolve=lambda _, i, slug: get_post_by_slug(slug)),
    'posts': GraphQLField(GraphQLList(PostPreviewType), args={
        'page': GraphQLInt, 'limit': GraphQLInt, 'category': GraphQLString, 'tag': GraphQLString
    }, resolve=lambda _, i, page=1, limit=10, category=None, tag=None: get_posts(page, limit, category, tag)),
    'searchPosts': GraphQLField(GraphQLList(PostPreviewType), args={'q': GraphQLNonNull(GraphQLString), 'limit': GraphQLInt}, resolve=lambda _, i, q, limit=10: search_posts(q, limit)),
})

# MUTATION
Mutation = GraphQLObjectType('Mutation', {
    'createPost': GraphQLField(GraphQLInt, args={'input': GraphQLNonNull(PostInput)}, resolve=lambda _, i, input: create_post(input)),
    'createCategory': GraphQLField(GraphQLInt, args={'name': GraphQLNonNull(GraphQLString), 'slug': GraphQLNonNull(GraphQLString), 'description': GraphQLString}, resolve=lambda _, i, **kw: create_category(**kw)),
})

schema = GraphQLSchema(query=Query, mutation=Mutation)