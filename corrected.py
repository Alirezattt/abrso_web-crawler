import requests
import json
import os
import time
from datetime import datetime
import hashlib
import random


proxies = {
    "http": "http://127.0.0.1:12334",
    "https": "http://127.0.0.1:12334",
}


url = "https://api.divar.ir/v8/postlist/w/search"
detail_url_template = "https://api.divar.ir/v8/posts-v2/web/{token}"


payload_template = {
    "pagination_data": {
        "@type": "type.googleapis.com/post_list.PaginationData",
        "last_post_date": None,  # Will be set dynamically
        "page": 0,
        "layer_page": 1  # Fixed to 1 (like your working code)
    },
    "disable_recommendation": False,
    "map_state": {"camera_info": {"bbox": {}}},
    "search_data": {
        "form_data": {
            "data": {
                "sort": {"str": {"value": "sort_date"}},
                "category": {"str": {"value": "temporary-rent"}}
            }
        },
        "server_payload": {
            "@type": "type.googleapis.com/widgets.SearchData.ServerPayload",
            "additional_form_data": {}
        }
    }
}


headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


non_200_count = 0
max_non_200 = 100
max_non_widget = 10


base_dir = "divar/temporary-rent/sort_date"
if not os.path.exists(base_dir):
    os.makedirs(base_dir)


processed_tokens = set()


city_id = 1
while non_200_count < max_non_200:
    print(f"Processing city_id: {city_id}")
    
    # Start with a fixed known old date to fetch newest first, can be customized
    last_post_date = "2025-05-08T10:39:16.934211626Z"
    
    no_more_results = 0
    
    for page in range(151):
        if no_more_results > max_non_widget:
            break
            
        print(f"  Processing page: {page}")
        
        payload = dict(payload_template)  # create a fresh copy each loop
        payload["city_ids"] = [str(city_id)]
        payload["pagination_data"]["page"] = page
        payload["pagination_data"]["layer_page"] = 1  # fixed to 1 as in original working code
        payload["pagination_data"]["last_post_date"] = last_post_date  # update dynamically
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), proxies=proxies)
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                list_widgets = data.get("list_widgets", [])
                
                if not list_widgets:
                    print("  No widgets found, moving to next city")
                    no_more_results += 1
                    continue
                
                # Update last_post_date using the last widget's sort_date if available
                try:
                    last_widget = list_widgets[-1]
                    if ("action_log" in last_widget and 
                        "server_side_info" in last_widget["action_log"] and
                        "info" in last_widget["action_log"]["server_side_info"] and
                        "sort_date" in last_widget["action_log"]["server_side_info"]["info"]):
                        last_post_date = last_widget["action_log"]["server_side_info"]["info"]["sort_date"]
                        print(f"  Updated last_post_date: {last_post_date}")
                    else:
                        print("  Could not find sort_date in response structure")
                except (KeyError, IndexError) as e:
                    print(f"  Could not update last_post_date: {e}")
                
                new_items_count = 0
                for widget in list_widgets:
                    try:
                        web_info = widget.get("data", {}).get("action", {}).get("payload", {}).get("web_info", {})
                        if not web_info:
                            continue
                        
                        token = widget.get("data", {}).get("token")
                        if not token:
                            content_str = json.dumps(widget, sort_keys=True)
                            token = hashlib.md5(content_str.encode("utf-8")).hexdigest()
                        
                        if token in processed_tokens:
                            print(f"  Skipping duplicate item with token: {token}")
                            continue
                        
                        processed_tokens.add(token)
                        new_items_count += 1
                        
                        city_name = web_info.get("city_persian")
                        district_name = web_info.get("district_persian")
                        if not city_name:
                            continue
                        
                        city_dir = os.path.join(base_dir, city_name)
                        os.makedirs(city_dir, exist_ok=True)
                        
                        save_dir = city_dir
                        if district_name:
                            district_dir = os.path.join(city_dir, district_name)
                            os.makedirs(district_dir, exist_ok=True)
                            save_dir = district_dir
                        
                        detail_url = detail_url_template.format(token=token)
                        detail_response = requests.get(detail_url, headers=headers, proxies=proxies)
                        
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            filename = os.path.join(save_dir, f"{token}.json")
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(detail_data, f, ensure_ascii=False, indent=2)
                            print(f" page: {page}, Saved detailed data for token: {token}")
                        else:
                            print(f"  Failed to get detailed data for token: {token}, status: {detail_response.status_code}")
                            filename = os.path.join(save_dir, f"{token}_widget.json")
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(widget, f, ensure_ascii=False, indent=2)
                        
                        time.sleep(random.uniform(0.8, 1.7))
                    
                    except Exception as e:
                        print(f"  Error processing widget: {e}")
                
                print(f"  Saved {new_items_count} new items on this page")
                if new_items_count == 0 and page > 0:
                    print("  No new items found, moving to next city")
                    no_more_results += 1
            
            else:
                non_200_count += 1
                print(f"  Non-200 response count: {non_200_count}/{max_non_200}")
                if non_200_count >= max_non_200:
                    print("Reached maximum number of non-200 responses. Stopping.")
                    break
            
            time.sleep(4)
        
        except Exception as e:
            print(f"  Request error: {e}")
            non_200_count += 1
    
    city_id += 1


print(f"Script completed. Processed up to city_id: {city_id-1}")
print(f"Data saved in {os.path.abspath(base_dir)}")
print(f"Total unique items processed: {len(processed_tokens)}")
