from embeddings import get_recommended_wines
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

results = get_recommended_wines(
    query = "warm spiced, full-bodied red wine",
    price_min = 0,
    price_max = 50,
    countries = ["Italy"]
)
for i, wine in enumerate(results):
    print(f"  #{i+1} {wine['title'] or wine['winery']}"
          f" ({wine['variety']})"
          f" ${wine['price']:.0f} | {wine['points']}pts"
          f" | similarity: {wine['similarity']}")
    print(f"       {wine['description'][:100]}...")
    print()
