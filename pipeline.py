from agents import writer_chain , critic_chain
import tools
import sys
import time

def run_research_pipeline(topic : str) -> dict:

    state = {}

    #search agent working
    print("\n"+"-"*50)
    print("Step 1 - search agent is working ...")
    print("="*50)

    try:
        raw_results = tools.web_search_direct(query=topic, max_results=3)
        formatted_search = []
        urls_to_scrape = []
        for r in raw_results:
            formatted_search.append(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('content')[:300]}\n")
            if "url" in r:
                urls_to_scrape.append(r["url"])
                
        state["search_results"] = "\n---\n".join(formatted_search)
        state["urls_to_scrape"] = urls_to_scrape
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\n⚠️  QUOTA EXHAUSTED: You've hit the Gemini API free tier limit (20 requests/day)")
            sys.exit(1)
        raise

    print("\n search result ",state['search_results'])

    # step 2 - reader agent
    print("\n"+"="*50)
    print("Step 2 - Reader agent is scraping top resources ...")
    print("="*50)

    try:
        state['scraped_content'] = tools.concurrent_scrape(state["urls_to_scrape"])
    except Exception as e:
        raise

    print("\n scraped content: \n",state['scraped_content'])

    # step 3 - writer chain

    print("\n"+"="*50)
    print("Step 3 - Writer is drafting the report ...")
    print("="*50)

    research_combined = (
        f"SEARCH RESULTS : \n {state['search_results']} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
    )

    try:
        state["report"] = writer_chain.invoke({
            "topic" : topic,
            "research" : research_combined
        })
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\n⚠️  QUOTA EXHAUSTED: You've hit the Gemini API free tier limit (20 requests/day)")
            print("\n📋 To fix this:")
            print("1. Upgrade to a PAID Gemini API plan: https://console.cloud.google.com/billing")
            print("2. OR wait until tomorrow when the quota resets")
            print("3. OR check if billing is enabled on your Google Cloud project")
            print("\n🔗 Monitor usage: https://ai.dev/rate-limit")
            sys.exit(1)
        raise

    print("\n Final Report\n",state['report'])

    # critic report

    print("\n"+"="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    try:
        state["feedback"]=critic_chain.invoke({
            "report":state['report']
        })
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\n⚠️  QUOTA EXHAUSTED: You've hit the Gemini API free tier limit (20 requests/day)")
            print("\n📋 To fix this:")
            print("1. Upgrade to a PAID Gemini API plan: https://console.cloud.google.com/billing")
            print("2. OR wait until tomorrow when the quota resets")
            print("3. OR check if billing is enabled on your Google Cloud project")
            print("\n🔗 Monitor usage: https://ai.dev/rate-limit")
            sys.exit(1)
        raise

    print("\n critic report \n", state['feedback'])

    return state

if __name__ == "__main__":
    try:
        # Check if topic is provided as command-line argument
        if len(sys.argv) > 1:
            topic = " ".join(sys.argv[1:])
        else:
            topic = input("\n Enter a research topic : ")
        
        if topic.strip():
            run_research_pipeline(topic)
        else:
            print("Error: Topic cannot be empty.")
    except KeyboardInterrupt:
        print("\n\nResearch interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)