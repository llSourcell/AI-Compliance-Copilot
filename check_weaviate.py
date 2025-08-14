import weaviate
from weaviate.connect import ConnectionParams

client = weaviate.WeaviateClient(ConnectionParams.from_params(
    http_host="weaviate",
    http_port=8080,
    http_secure=False,
    grpc_host="weaviate",
    grpc_port=50051,
    grpc_secure=False,
))
client.connect()

collection = client.collections.get("ComplianceDocument")
count = collection.aggregate.over_all(total_count=True).total_count
print(f"Number of objects in ComplianceDocument: {count}")

client.close()
