import requests
import json
import os
import time
from datetime import datetime, timezone
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
        "layer_page": 0  
    },
    "disable_recommendation": False,
    "map_state": {"camera_info": {"bbox": {}}},
    "search_data": {
        "form_data": {
            "data": {
                "sort": {"str": {"value": "sort_date"}},
                "category": {"str": {"value": "parts-accessories"}}
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


base_dir = "divar/car-accessories/sort_date"
if not os.path.exists(base_dir):
    os.makedirs(base_dir)


processed_tokens = set()

common = ["خودرو", "ماشین"]
separate = ["تزئیناتی","لوازم امنیت و حفاظت خودرو","GPS ردیاب و","دزدگیر","لوازم اسپرت","سیستم صوتی وتصویری"]
combinations = []

for i in common :
    for j in separate :
        combinations.append(f"{i} {j}")

import requests
def find_phonenumber(token="wZzK82uW", uuid="a72bcf2d-e79e-4682-ad9a-847b1f46bb57"):
    url = f"https://api.divar.ir/v8/postcontact/web/contact_info_v2/{token}"
    headers = {

        "Authorization": "Basic eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaWQiOiI0NGYyNmM3Ni05NmM3LTRkNTktYmQyZi1lYjdiNzEwNzZjODEiLCJ1aWQiOiJmMjY5NTg5NC0xYjQ0LTQxOTAtOTJkMi04NDUzNDY1N2FiODYiLCJ1c2VyIjoiMDkwMjQ2MzY1NjUiLCJ2ZXJpZmllZF90aW1lIjoxNzYwNTkwMTU5LCJpc3MiOiJhdXRoIiwidXNlci10eXBlIjoicGVyc29uYWwiLCJ1c2VyLXR5cGUtZmEiOiLZvtmG2YQg2LTYrti124wiLCJleHAiOjE3NjMxODIxNTksImlhdCI6MTc2MDU5MDE1OX0.YOTqNvwn0F2PT7Fkfl0ElX0onbMQkhfap5_gN8tgD-E",
    }
    payload = {
        "contact_uuid": uuid
    }
    response = requests.post(url, headers=headers, json=payload)

    # #print(response.text)
    # if response.status_code == 200:
    #     data = response.json()
    #     #print(data)
    #     return data["widget_list"][0]["data"]["action"]["payload"]["phone_number"]
    # else:
    #     return None
    return response



city_id = 877
for i in combinations :
    city_id = 877
    while non_200_count < max_non_200:
        print(f"Processing city_id: {city_id}")
        
        # Start with a fixed known old date to fetch newest first, can be customized
        last_post_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().time().microsecond * 1000:09d}Z"
        
        no_more_results = 0
        
        for page in range(151):
            if no_more_results > max_non_widget:
                break
                
            print(f"  Processing page: {page}")
            
            payload = dict(payload_template)  # create a fresh copy each loop
            payload["search_data"]["query"] = i
            payload["city_ids"] = [str(city_id)]
            payload["pagination_data"]["page"] = page
            payload["pagination_data"]["layer_page"] = page
            payload["pagination_data"]["last_post_date"] = last_post_date  # update dynamically
            
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload))
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
                            detail_response = requests.get(detail_url, headers=headers)
                            time.sleep(random.uniform(1, 4))
                            phonenumber_response = find_phonenumber(token=token, uuid=detail_response.json()["contact"]["contact_uuid"])
                            
                            if detail_response.status_code == 200 and phonenumber_response.status_code == 200:
                                detail_data = detail_response.json()
                                phone_number = phonenumber_response.json()["widget_list"][0]["data"]["action"]["payload"]["phone_number"],
                                save_data = ["دیوار",
                                             i,
                                             phone_number,
                                             detail_data["seo"]["post_seo_schema"]["name"],
                                             detail_data["city"]["parent_id"],
                                             city_name,
                                             detail_data["seo"]["post_seo_schema"]["web_info"]["category_slug_persian"],
                                             detail_data["seo"]["post_seo_schema"]["description"],
                                             detail_data["seo"]["post_seo_schema"]["url"],
                                             ]
                                
                                import csv
                                csv_path = "document.csv"

                                header = [
                                    "Platform",
                                    "Index",
                                    "Phone",
                                    "Name",
                                    "ParentCityID",
                                    "CityName",
                                    "CategorySlugPersian",
                                    "Description",
                                    "URL",
                                ]
                                with open(csv_path, 'a', newline='', encoding="utf-8") as csvfile:
                                    writer = csv.writer(csvfile)
                                    writer.writerow(save_data)
                                    
                                filename = os.path.join(save_dir, f"{token}.json")
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump({**detail_data,**{"phone_number" :  phone_number}}, f, ensure_ascii=False, indent=2)
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
        if city_id > 877 :
            break


print(f"Script completed. Processed up to city_id: {city_id-1}")
print(f"Data saved in {os.path.abspath(base_dir)}")
print(f"Total unique items processed: {len(processed_tokens)}")
