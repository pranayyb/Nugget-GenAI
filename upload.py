import json
import chromadb
from chromadb.utils import embedding_functions

with open("lucknow_restaurants.json", "r") as file:
    restaurants_data = json.load(file)

client = chromadb.PersistentClient("./chroma_db")

embedding_function = embedding_functions.DefaultEmbeddingFunction()

restaurant_collection = client.create_collection(
    name="restaurants",
    embedding_function=embedding_function,
    metadata={"description": "Restaurant information in Lucknow"},
)

for i, restaurant in enumerate(restaurants_data):
    restaurant_text = f"Name: {restaurant.get('name', 'N/A')}\n"

    if restaurant.get("locations"):
        restaurant_text += "Locations:\n"
        for location in restaurant["locations"]:
            restaurant_text += f"- {location}\n"

    if restaurant.get("menu"):
        restaurant_text += "Menu Items:\n"
        for item in restaurant["menu"]:
            item_text = f"- {item.get('name', 'Unnamed Item')}"
            description = item.get("description")
            if description:
                item_text += f": {description}"
            price = item.get("price")
            if price:
                item_text += f" ({price})"
            restaurant_text += item_text + "\n"

    if restaurant.get("hours"):
        restaurant_text += f"Hours: {restaurant['hours']}\n"

    if restaurant.get("contact"):
        restaurant_text += "Contact:\n"
        for key, value in restaurant["contact"].items():
            restaurant_text += f"- {key}: {value}\n"

    if restaurant.get("special"):
        restaurant_text += "Special Information:\n"
        for special in restaurant["special"]:
            restaurant_text += f"- {special}\n"

    metadata = {
        "name": restaurant.get("name", "Unknown"),
        "type": "restaurant",
    }

    if restaurant.get("hours"):
        metadata["hours"] = restaurant["hours"]

    restaurant_collection.add(
        documents=[restaurant_text], metadatas=[metadata], ids=[f"restaurant_{i+1}"]
    )


print(f"Successfully added {len(restaurants_data)} restaurants to ChromaDB collection")

# results = restaurant_collection.query(
#     query_texts=["what is the price of kebab?"], n_results=10
# )
# print(results)
