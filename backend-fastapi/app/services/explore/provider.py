import asyncio
import time
from typing import Dict, List, Optional, Any

from app.services.explore.nominatim import nominatim_service
from app.services.explore.overpass import overpass_service
from app.services.explore.wikimedia import wikimedia_service

# In-memory place cache (TTL: 6 hours)
_PLACES_STORE: Dict[str, Dict[str, Any]] = {}
_DESTINATION_STORE: Dict[str, Dict[str, Any]] = {}

FEATURED_DESTINATIONS_DATA = [
    {
        "destination": "Hyderabad",
        "country": "India",
        "lat": 17.385044,
        "lon": 78.486671,
        "description": "Hyderabad is celebrated for its 400-year-old Nizami heritage, architectural monuments, and iconic cuisine.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/800px-Charminar_Hyderabad_1.jpg",
        "overview": "The City of Pearls seamlessly blends ancient Qutb Shahi grandeur with modern IT corridors in HITEC City.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_charminar",
                "place_id": "osm_way_charminar",
                "provider": "openstreetmap",
                "name": "Charminar",
                "category": "attraction",
                "address": "Charminar Rd, Char Kaman, Ghansi Bazaar, Hyderabad 500002",
                "lat": 17.3615636,
                "lon": 78.4746645,
                "description": "Iconic 16th-century mosque and landmark with four grand arches and ornate 48.7m minarets.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Charminar_Hyderabad_1.jpg/800px-Charminar_Hyderabad_1.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "wikipedia_url": "https://en.wikipedia.org/wiki/Charminar",
                "tags": ["Historical Landmark", "Monument", "Architecture"]
            },
            {
                "id": "osm_way_golconda",
                "place_id": "osm_way_golconda",
                "provider": "openstreetmap",
                "name": "Golconda Fort",
                "category": "historic",
                "address": "Khair Complex, Ibrahim Bagh, Hyderabad 500008",
                "lat": 17.3833075,
                "lon": 78.4010536,
                "description": "Historic fortified citadel famous for acoustic architecture and provenance of the Koh-i-Noor diamond.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Golconda_Fort_Hyderabad.jpg/800px-Golconda_Fort_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "wikipedia_url": "https://en.wikipedia.org/wiki/Golconda_Fort",
                "tags": ["Citadel", "Fortress", "Acoustics", "Heritage"]
            },
            {
                "id": "osm_way_ramoji",
                "place_id": "osm_way_ramoji",
                "provider": "openstreetmap",
                "name": "Ramoji Film City",
                "category": "activity",
                "address": "Ramoji Film City Main Rd, Hayathnagar, Hyderabad 501512",
                "lat": 17.254318,
                "lon": 78.680766,
                "description": "World's largest integrated film studio complex spanning 1,666 acres with movie sets and rides.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Ramoji_Film_City_Central_Street.jpg/800px-Ramoji_Film_City_Central_Street.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Film Studio", "Theme Park", "Entertainment"]
            },
            {
                "id": "osm_node_salarjung",
                "place_id": "osm_node_salarjung",
                "provider": "openstreetmap",
                "name": "Salar Jung Museum",
                "category": "museum",
                "address": "Salar Jung Rd, Darulshifa, Hyderabad 500002",
                "lat": 17.3713,
                "lon": 78.4804,
                "description": "Prestigious art museum on the Musi River housing one of the world's largest one-man art collections.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Salar_Jung_Museum_Hyderabad.jpg/800px-Salar_Jung_Museum_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Art Museum", "Sculptures", "Antiques"]
            },
            {
                "id": "osm_way_chowmahalla",
                "place_id": "osm_way_chowmahalla",
                "provider": "openstreetmap",
                "name": "Chowmahalla Palace",
                "category": "historic",
                "address": "Motigalli, Khilwat, Hyderabad 500002",
                "lat": 17.3578,
                "lon": 78.4717,
                "description": "Opulent 18th-century palace complex of the Nizams featuring neoclassical courtyards and vintage cars.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Chowmahalla_Palace_Durbar_Hall.jpg/800px-Chowmahalla_Palace_Durbar_Hall.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Royal Palace", "Durbar Hall", "Architecture"]
            },
            {
                "id": "osm_node_birla_mandir",
                "place_id": "osm_node_birla_mandir",
                "provider": "openstreetmap",
                "name": "Birla Mandir",
                "category": "attraction",
                "address": "Hill Fort Rd, Ambedkar Colony, Khairtabad, Hyderabad 500004",
                "lat": 17.4062,
                "lon": 78.4691,
                "description": "White Rajasthani marble temple perched atop Naubat Pahad overlooking Hussain Sagar.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Birla_Mandir_Hyderabad.jpg/800px-Birla_Mandir_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Temple", "Marble Architecture", "Panoramic View"]
            },
            {
                "id": "osm_node_hussain_sagar",
                "place_id": "osm_node_hussain_sagar",
                "provider": "openstreetmap",
                "name": "Hussain Sagar Lake & Buddha Statue",
                "category": "park",
                "address": "Necklace Rd, Tank Bund, Hyderabad 500003",
                "lat": 17.4239,
                "lon": 78.4738,
                "description": "Heart-shaped 16th-century lake featuring an 18-meter monolith Buddha statue at Gibraltar Rock.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Buddha_Statue_Hyderabad.jpg/800px-Buddha_Statue_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Lake", "Buddha Monolith", "Boating"]
            },
            {
                "id": "osm_way_qutb_shahi",
                "place_id": "osm_way_qutb_shahi",
                "provider": "openstreetmap",
                "name": "Qutb Shahi Tombs",
                "category": "historic",
                "address": "Fort Rd, Toli Chowki, Hyderabad 500008",
                "lat": 17.3941,
                "lon": 78.3965,
                "description": "Grand domed royal mausoleums of the seven Qutb Shahi rulers surrounded by landscaped gardens.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Qutb_Shahi_Tombs_Complex.jpg/800px-Qutb_Shahi_Tombs_Complex.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Mausoleum", "Qutb Shahi", "Heritage"]
            },
            {
                "id": "osm_node_shilparamam",
                "place_id": "osm_node_shilparamam",
                "provider": "openstreetmap",
                "name": "Shilparamam Arts & Crafts Village",
                "category": "activity",
                "address": "HITEC City Main Rd, Madhapur, Hyderabad 500081",
                "lat": 17.4526,
                "lon": 78.3780,
                "description": "Sprawling traditional crafts village showcasing artisanal handlooms, pottery, and folk performances.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Shilparamam_Crafts_Village_Hyderabad.jpg/800px-Shilparamam_Crafts_Village_Hyderabad.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Handicrafts", "Folk Culture", "Artisans"]
            },
            {
                "id": "osm_node_nehru_zoo",
                "place_id": "osm_node_nehru_zoo",
                "provider": "openstreetmap",
                "name": "Nehru Zoological Park",
                "category": "park",
                "address": "Zoo Park Rd, Bahadurpura, Hyderabad 500064",
                "lat": 17.3508,
                "lon": 78.4516,
                "description": "380-acre zoological park featuring safari parks, nocturnal animal house, and wildlife conservation.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Zoological Park", "Safari", "Wildlife"]
            },
            {
                "id": "osm_node_taj_falaknuma",
                "place_id": "osm_node_taj_falaknuma",
                "provider": "openstreetmap",
                "name": "Taj Falaknuma Palace",
                "category": "hotel",
                "address": "Engine Bowli, Fatima Nagar, Falaknuma, Hyderabad 500053",
                "lat": 17.3314,
                "lon": 78.4674,
                "description": "Restored 1894 royal palace of the Nizam transformed into an ultra-luxury heritage palace hotel.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Falaknuma_Palace_Facade.jpg/800px-Falaknuma_Palace_Facade.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Luxury Palace", "Heritage Hotel", "Fine Dining"]
            },
            {
                "id": "osm_node_taj_krishna",
                "place_id": "osm_node_taj_krishna",
                "provider": "openstreetmap",
                "name": "Taj Krishna",
                "category": "hotel",
                "address": "Road No 1, Banjara Hills, Hyderabad 500034",
                "lat": 17.4168,
                "lon": 78.4485,
                "description": "5-star luxury hotel in Banjara Hills with manicured lawns, outdoor pool, and specialty dining.",
                "image_url": None,
                "image_verified": False,
                "tags": ["5-Star Hotel", "Banjara Hills", "Spa"]
            },
            {
                "id": "osm_node_taj_banjara",
                "place_id": "osm_node_taj_banjara",
                "provider": "openstreetmap",
                "name": "Taj Banjara",
                "category": "hotel",
                "address": "Road No 1, Mithila Nagar, Banjara Hills, Hyderabad 500034",
                "lat": 17.4172,
                "lon": 78.4496,
                "description": "Upscale lakeside hotel offering tranquil waterside dining and modern luxury rooms.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Lakeside Hotel", "Banjara Hills", "Dining"]
            },
            {
                "id": "osm_node_itc_kohenur",
                "place_id": "osm_node_itc_kohenur",
                "provider": "openstreetmap",
                "name": "ITC Kohenur",
                "category": "hotel",
                "address": "Plot No 5, Knowledge City, Madhapur, Hyderabad 500081",
                "lat": 17.4338,
                "lon": 78.3789,
                "description": "Luxury hotel overlooking Durgam Cheruvu lake with award-winning progressive restaurants.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Luxury Hotel", "HITEC City", "Lake View"]
            },
            {
                "id": "osm_node_paradise_biryani",
                "place_id": "osm_node_paradise_biryani",
                "provider": "openstreetmap",
                "name": "Paradise Biryani",
                "category": "restaurant",
                "address": "MG Rd, Paradise Circle, Secunderabad 500003",
                "lat": 17.4411,
                "lon": 78.4984,
                "description": "Legendary institution founded in 1953 celebrated for authentic Hyderabadi Dum Biryani.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Biryani", "Hyderabadi Cuisine", "Historic Dining"]
            },
            {
                "id": "osm_node_bawarchi",
                "place_id": "osm_node_bawarchi",
                "provider": "openstreetmap",
                "name": "Bawarchi Restaurant",
                "category": "restaurant",
                "address": "RTC X Roads, Chikkadpally, Hyderabad 500020",
                "lat": 17.4045,
                "lon": 78.4987,
                "description": "Famous local dining destination renowned for spicy Hyderabadi biryani and grilled kebabs.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Biryani", "Mughlai", "Local Favorite"]
            },
            {
                "id": "osm_node_cafe_niloufer",
                "place_id": "osm_node_cafe_niloufer",
                "provider": "openstreetmap",
                "name": "Cafe Niloufer",
                "category": "cafe",
                "address": "Red Hills, Lakdikapul, Hyderabad 500004",
                "lat": 17.3995,
                "lon": 78.4619,
                "description": "Historic cafe serving signature Hyderabadi Irani Chai, Osmania biscuits, and bun maska.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Irani Chai", "Osmania Biscuits", "Heritage Cafe"]
            },
            {
                "id": "osm_node_karachi_bakery",
                "place_id": "osm_node_karachi_bakery",
                "provider": "openstreetmap",
                "name": "Karachi Bakery",
                "category": "cafe",
                "address": "Mozamjahi Market, Abids, Hyderabad 500001",
                "lat": 17.3876,
                "lon": 78.4772,
                "description": "Iconic 1953 bakery celebrated for handmade fruit biscuits, plum cakes, and pastries.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Bakery", "Fruit Biscuits", "Souvenirs"]
            },
            {
                "id": "osm_node_chutneys",
                "place_id": "osm_node_chutneys",
                "provider": "openstreetmap",
                "name": "Chutneys",
                "category": "restaurant",
                "address": "Road No 3, Banjara Hills, Hyderabad 500034",
                "lat": 17.4245,
                "lon": 78.4412,
                "description": "Beloved South Indian vegetarian restaurant famous for Guntur idlis and 6 unique chutneys.",
                "image_url": None,
                "image_verified": False,
                "tags": ["South Indian", "Vegetarian", "Dosa & Idli"]
            },
            {
                "id": "osm_node_durgam_cheruvu",
                "place_id": "osm_node_durgam_cheruvu",
                "provider": "openstreetmap",
                "name": "Durgam Cheruvu & Cable Bridge",
                "category": "park",
                "address": "CBI Colony, Jubilee Hills, Hyderabad 500033",
                "lat": 17.4332,
                "lon": 78.3842,
                "description": "Picturesque freshwater lake surrounded by 2,500-million-year-old granite rock formations and illuminated bridge.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Secret Lake", "Cable Bridge", "Walking Trail"]
            },
            {
                "id": "osm_node_kbr_park",
                "place_id": "osm_node_kbr_park",
                "provider": "openstreetmap",
                "name": "KBR National Park",
                "category": "park",
                "address": "Road No 2, Jubilee Hills, Hyderabad 500034",
                "lat": 17.4265,
                "lon": 78.4230,
                "description": "390-acre urban national park home to rich avian fauna, peacocks, and Chiran Palace.",
                "image_url": None,
                "image_verified": False,
                "tags": ["National Park", "Nature Trail", "Peacocks"]
            },
            {
                "id": "osm_node_paigah_tombs",
                "place_id": "osm_node_paigah_tombs",
                "provider": "openstreetmap",
                "name": "Paigah Tombs",
                "category": "historic",
                "address": "Pisall Banda, Santosh Nagar, Hyderabad 500059",
                "lat": 17.3442,
                "lon": 78.5048,
                "description": "Intricately carved stucco and marble mausoleums of the aristocratic Paigah nobility.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Stucco Art", "Marble Inlay", "Nobility Tombs"]
            },
            {
                "id": "osm_node_mecca_masjid",
                "place_id": "osm_node_mecca_masjid",
                "provider": "openstreetmap",
                "name": "Mecca Masjid",
                "category": "attraction",
                "address": "Charminar South, Ghansi Bazaar, Hyderabad 500002",
                "lat": 17.3610,
                "lon": 78.4735,
                "description": "One of the oldest and largest mosques in India, constructed with bricks made from soil brought from Mecca.",
                "image_url": None,
                "image_verified": False,
                "tags": ["Historic Mosque", "Granite Arches", "Heritage"]
            }
        ]
    },
    {
        "destination": "Goa",
        "country": "India",
        "lat": 15.299326,
        "lon": 74.123996,
        "description": "Goa is renowned for its golden coastline, Portuguese colonial architecture, and tropical spice plantations.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/800px-Baga_Beach_North_Goa.jpg",
        "overview": "India's premier beach paradise offering heritage churches, water sports, and vibrant coastal dining.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_node_baga_beach",
                "place_id": "osm_node_baga_beach",
                "provider": "openstreetmap",
                "name": "Baga Beach",
                "category": "attraction",
                "address": "Baga, North Goa 403516",
                "lat": 15.5553,
                "lon": 73.7517,
                "description": "Popular North Goa beach destination known for water sports, nightlife, and seaside shacks.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Baga_Beach_North_Goa.jpg/800px-Baga_Beach_North_Goa.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Beach", "Water Sports", "Coastal"]
            },
            {
                "id": "osm_way_fort_aguada",
                "place_id": "osm_way_fort_aguada",
                "provider": "openstreetmap",
                "name": "Fort Aguada",
                "category": "historic",
                "address": "Sinquerim, Candolim, Goa 403515",
                "lat": 15.4924,
                "lon": 73.7736,
                "description": "17th-century Portuguese fortress and lighthouse commanding sweeping views of the Arabian Sea.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Fort_Aguada_Goa.jpg/800px-Fort_Aguada_Goa.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Portuguese Fort", "Lighthouse", "Sea View"]
            },
            {
                "id": "osm_way_bom_jesus",
                "place_id": "osm_way_bom_jesus",
                "provider": "openstreetmap",
                "name": "Basilica of Bom Jesus",
                "category": "historic",
                "address": "Old Goa Rd, Bainguinim, Goa 403402",
                "lat": 15.5008,
                "lon": 73.9116,
                "description": "UNESCO World Heritage Baroque basilica holding the mortal remains of St. Francis Xavier.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Basilica_of_Bom_Jesus_Goa.jpg/800px-Basilica_of_Bom_Jesus_Goa.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["UNESCO Site", "Baroque Church", "Heritage"]
            },
            {
                "id": "osm_node_dudhsagar",
                "place_id": "osm_node_dudhsagar",
                "provider": "openstreetmap",
                "name": "Dudhsagar Waterfalls",
                "category": "park",
                "address": "Sonaulim, Goa 403410",
                "lat": 15.3144,
                "lon": 74.3143,
                "description": "Majestic four-tiered waterfall on the Mandovi River descending 310 meters through lush Western Ghats.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Dudhsagar_Falls_Goa.jpg/800px-Dudhsagar_Falls_Goa.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Waterfall", "Western Ghats", "Trekking"]
            }
        ]
    },
    {
        "destination": "Bengaluru",
        "country": "India",
        "lat": 12.971599,
        "lon": 77.594566,
        "description": "The Garden City and Silicon Valley of India, known for lush parks, microbreweries, and historical palaces.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/800px-Lalbagh_Glass_house_Bangalore.jpg",
        "overview": "Cosmopolitan tech hub with pleasant year-round climate, Victorian parks, and craft dining.",
        "best_time_to_visit": "September to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_lalbagh",
                "place_id": "osm_way_lalbagh",
                "provider": "openstreetmap",
                "name": "Lalbagh Botanical Garden",
                "category": "park",
                "address": "Mavalli, Bengaluru, Karnataka 560004",
                "lat": 12.9507,
                "lon": 77.5848,
                "description": "Historic 240-acre botanical garden featuring the famous 19th-century Glass House.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lalbagh_Glass_house_Bangalore.jpg/800px-Lalbagh_Glass_house_Bangalore.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Botanical Garden", "Heritage", "Nature"]
            },
            {
                "id": "osm_way_bangalore_palace",
                "place_id": "osm_way_bangalore_palace",
                "provider": "openstreetmap",
                "name": "Bangalore Palace",
                "category": "historic",
                "address": "Vasanth Nagar, Bengaluru, Karnataka 560052",
                "lat": 12.9988,
                "lon": 77.5921,
                "description": "19th-century Tudor-style royal palace inspired by England's Windsor Castle with woodcarvings.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Bangalore_Palace_Facade.jpg/800px-Bangalore_Palace_Facade.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Tudor Palace", "Royal Heritage", "Architecture"]
            },
            {
                "id": "osm_node_cubbon_park",
                "place_id": "osm_node_cubbon_park",
                "provider": "openstreetmap",
                "name": "Cubbon Park",
                "category": "park",
                "address": "Kasturba Rd, Sampangi Rama Nagara, Bengaluru 560001",
                "lat": 12.9738,
                "lon": 77.5907,
                "description": "300-acre green lung in central Bangalore featuring colonial red buildings and bamboo groves.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Cubbon_Park_Bangalore.jpg/800px-Cubbon_Park_Bangalore.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Urban Park", "Walking Trail", "Colonial Buildings"]
            }
        ]
    },
    {
        "destination": "Delhi",
        "country": "India",
        "lat": 28.613939,
        "lon": 77.209021,
        "description": "India's vibrant capital, spanning centuries of Mughal, British, and modern monuments.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/800px-India_Gate_in_New_Delhi_03-2016.jpg",
        "overview": "A vast cultural capital rich with UNESCO World Heritage sites and renowned street food.",
        "best_time_to_visit": "October to March",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_india_gate",
                "place_id": "osm_way_india_gate",
                "provider": "openstreetmap",
                "name": "India Gate",
                "category": "historic",
                "address": "Kartavya Path, India Gate, New Delhi 110001",
                "lat": 28.6129,
                "lon": 77.2295,
                "description": "Prominent 42-meter-high war memorial arch honoring Indian soldiers.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/India_Gate_in_New_Delhi_03-2016.jpg/800px-India_Gate_in_New_Delhi_03-2016.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Monument", "Memorial", "Landmark"]
            },
            {
                "id": "osm_way_red_fort",
                "place_id": "osm_way_red_fort",
                "provider": "openstreetmap",
                "name": "Red Fort",
                "category": "historic",
                "address": "Netaji Subhash Marg, Lal Qila, Chandni Chowk, Old Delhi 110006",
                "lat": 28.6562,
                "lon": 77.2410,
                "description": "Historic red sandstone fortress complex that served as the main residence of Mughal Emperors.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Red_Fort_Delhi.jpg/800px-Red_Fort_Delhi.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Mughal Fort", "UNESCO Site", "Heritage"]
            }
        ]
    },
    {
        "destination": "Mumbai",
        "country": "India",
        "lat": 18.922000,
        "lon": 72.834700,
        "description": "India's bustling financial and entertainment capital on the Arabian Sea.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Gateway_of_India_Mumbai_India.jpg/800px-Gateway_of_India_Mumbai_India.jpg",
        "overview": "The City of Dreams featuring Victorian Gothic architecture, sea promenades, and Bollywood.",
        "best_time_to_visit": "November to February",
        "currency": "INR (₹)",
        "highlights": [
            {
                "id": "osm_way_gateway_india",
                "place_id": "osm_way_gateway_india",
                "provider": "openstreetmap",
                "name": "Gateway of India",
                "category": "historic",
                "address": "Apollo Bandar, Colaba, Mumbai 400001",
                "lat": 18.9220,
                "lon": 72.8347,
                "description": "20th-century arch monument erected commemorating King George V's landing.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Gateway_of_India_Mumbai_India.jpg/800px-Gateway_of_India_Mumbai_India.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Monument", "Seafront", "Heritage"]
            }
        ]
    },
    {
        "destination": "Paris",
        "country": "France",
        "lat": 48.856614,
        "lon": 2.352222,
        "description": "The City of Light, globally renowned for fashion, art, gastronomy, and culture.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/800px-Tour_Eiffel_Wikimedia_Commons.jpg",
        "overview": "World capital of art, gastronomy, and timeless European elegance.",
        "best_time_to_visit": "April to October",
        "currency": "EUR (€)",
        "highlights": [
            {
                "id": "osm_way_eiffel_tower",
                "place_id": "osm_way_eiffel_tower",
                "provider": "openstreetmap",
                "name": "Eiffel Tower",
                "category": "attraction",
                "address": "Champ de Mars, 5 Av. Anatole France, 75007 Paris",
                "lat": 48.8584,
                "lon": 2.2945,
                "description": "Wrought-iron lattice tower on the Champ de Mars, global cultural icon of France.",
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/800px-Tour_Eiffel_Wikimedia_Commons.jpg",
                "image_verified": True,
                "image_source": "wikipedia",
                "tags": ["Iconic Monument", "Architecture", "Panoramic View"]
            }
        ]
    }
]


class ExploreProvider:
    """
    Unified OpenStreetMap, Nominatim, Overpass, and Wikimedia Explore Provider.
    100% Free & Open Public Architecture — No Google, No Mapbox, No Foursquare, No API keys required.
    """

    def __init__(self):
        self.nominatim = nominatim_service
        self.overpass = overpass_service
        self.wikimedia = wikimedia_service

        # Initialize memory store with pre-seeded featured items
        for fd in FEATURED_DESTINATIONS_DATA:
            _DESTINATION_STORE[fd["destination"].lower()] = fd
            for h in fd.get("highlights", []):
                _PLACES_STORE[h["id"]] = h

    async def _enrich_place(self, raw_place: Dict[str, Any], location_hint: str) -> Dict[str, Any]:
        """
        Enrich an Overpass place with verified Wikimedia data and format into the canonical place schema.
        """
        place_id = raw_place["id"]
        if place_id in _PLACES_STORE:
            return _PLACES_STORE[place_id]

        wiki_info = await self.wikimedia.resolve_place_entity(
            name=raw_place["name"],
            category=raw_place["category"],
            osm_wikipedia=raw_place.get("osm_wikipedia"),
            osm_wikidata=raw_place.get("osm_wikidata"),
            osm_image=raw_place.get("osm_image"),
            location_hint=location_hint
        )

        image_url = wiki_info.get("image_url") if wiki_info else None
        image_verified = bool(wiki_info and wiki_info.get("image_verified"))
        description = wiki_info.get("description") if wiki_info else None

        normalized = {
            "id": place_id,
            "place_id": place_id,  # For backward compatibility
            "provider": "openstreetmap",
            "provider_id": raw_place.get("provider_id", place_id),
            "name": raw_place["name"],
            "category": raw_place["category"],
            "address": raw_place["address"],
            "location": {
                "lat": raw_place["lat"],
                "lon": raw_place["lon"]
            },
            "lat": raw_place["lat"],
            "lon": raw_place["lon"],
            "description": description or f"{raw_place['category'].title()} in {location_hint.split(',')[0].strip() or 'the area'}.",
            "rating": None,
            "review_count": None,
            "image_url": image_url,
            "photos": [image_url] if image_url else [],
            "image_verified": image_verified,
            "image_source": wiki_info.get("image_source") if wiki_info else None,
            "image_source_url": wiki_info.get("image_source_url") if wiki_info else None,
            "image_author": None,
            "image_license": None,
            "wikipedia_url": wiki_info.get("wikipedia_url") if wiki_info else None,
            "wikidata_id": raw_place.get("osm_wikidata"),
            "phone": raw_place.get("phone"),
            "website": raw_place.get("website"),
            "opening_hours": raw_place.get("opening_hours"),
            "tags": raw_place.get("tags", []),
            "source": {
                "provider": "openstreetmap",
                "source_url": f"https://www.openstreetmap.org/{raw_place.get('provider_id', '')}"
            }
        }

        _PLACES_STORE[place_id] = normalized
        return normalized

    async def search_places(
        self,
        query: str,
        category: str = "all",
        page: int = 1,
        limit: int = 24
    ) -> Dict[str, Any]:
        """
        Full-featured place search: Geocoding via Nominatim -> Discovery via Overpass -> Enrichment via Wikimedia.
        """
        clean_q = query.strip()
        cat_lower = category.lower().strip()

        # 1. Geocode destination
        geo = await self.nominatim.geocode_destination(clean_q)
        if not geo:
            geo = await self.nominatim.geocode_destination("Hyderabad")

        lat = geo["lat"]
        lon = geo["lon"]
        display_name = geo["display_name"]
        dest_name = geo["name"]

        # 2. Collect known featured highlights for this destination
        dest_key = dest_name.lower()
        combined_places: List[Dict[str, Any]] = []
        seen_names = set()

        if dest_key in _DESTINATION_STORE:
            preset_places = _DESTINATION_STORE[dest_key].get("highlights", [])
            for p in preset_places:
                combined_places.append(p)
                seen_names.add(p["name"].lower())

        # 3. Discover live places via Overpass
        raw_places = await self.overpass.discover_places(lat=lat, lon=lon, category=cat_lower, radius=15000)

        # 4. Enrich discovered Overpass places concurrently
        enrich_tasks = [
            self._enrich_place(p, display_name)
            for p in raw_places[:48]
            if p["name"].lower() not in seen_names
        ]
        if enrich_tasks:
            enriched = await asyncio.gather(*enrich_tasks)
            for ep in enriched:
                combined_places.append(ep)

        # 5. Filter by category if requested
        if cat_lower not in ["all", "destinations"]:
            filtered_places = [
                p for p in combined_places
                if p["category"] == cat_lower.rstrip("s") or (cat_lower == "attractions" and p["category"] in ["attraction", "historic", "museum", "park"])
            ]
        else:
            filtered_places = combined_places

        # 6. Pagination
        total_count = len(filtered_places)
        start_idx = max(0, (page - 1) * limit)
        end_idx = start_idx + limit
        paged_places = filtered_places[start_idx:end_idx]
        has_more = end_idx < total_count

        # 7. Build Destination Guide Info
        dest_summary = await self.get_destination_details(dest_name)

        return {
            "query": clean_q,
            "category": cat_lower,
            "destination_info": dest_summary,
            "places": paged_places,
            "results": paged_places,  # For backward compatibility with existing frontend
            "page": page,
            "limit": limit,
            "total_results": total_count,
            "has_more": has_more
        }

    async def get_destination_details(self, destination_name: str) -> Optional[Dict[str, Any]]:
        """
        Get structured destination summary guide with verified overview and categorization.
        """
        clean_name = destination_name.strip()
        norm_key = clean_name.lower()

        if norm_key in _DESTINATION_STORE:
            return _DESTINATION_STORE[norm_key]

        geo = await self.nominatim.geocode_destination(clean_name)
        if not geo:
            return None

        # Fetch Wikipedia overview
        wiki_info = await self.wikimedia.get_wikipedia_page_summary(geo["name"])
        image_url = wiki_info.get("image_url") if wiki_info else None
        description = wiki_info.get("description") if wiki_info else None

        # Discover top places in this destination
        raw_places = await self.overpass.discover_places(lat=geo["lat"], lon=geo["lon"], category="all", radius=12000)
        enrich_tasks = [self._enrich_place(p, geo["display_name"]) for p in raw_places[:20]]
        enriched = await asyncio.gather(*enrich_tasks)

        guide = {
            "destination": geo["name"],
            "country": geo.get("country", ""),
            "lat": geo["lat"],
            "lon": geo["lon"],
            "description": description or f"Discover the culture, landmarks, and sights of {geo['name']}.",
            "image_url": image_url or (enriched[0].get("image_url") if enriched and enriched[0].get("image_verified") else None),
            "overview": description or f"{geo['name']} offers a rich blend of historic sights, dining, and accommodations.",
            "best_time_to_visit": "October to March",
            "currency": "INR (₹)" if geo.get("country") == "India" else "EUR (€)" if geo.get("country") == "France" else "USD ($)",
            "highlights": [p for p in enriched if p.get("category") in ["attraction", "historic", "museum", "park", "activity"]],
            "hotels": [p for p in enriched if p.get("category") == "hotel"],
            "restaurants": [p for p in enriched if p.get("category") in ["restaurant", "cafe"]],
            "attractions": [p for p in enriched if p.get("category") in ["attraction", "historic", "museum"]],
            "activities": [p for p in enriched if p.get("category") == "activity"],
        }

        _DESTINATION_STORE[norm_key] = guide
        return guide

    async def get_featured_destinations(self) -> List[Dict[str, Any]]:
        """
        Get list of top featured destination guides.
        """
        return list(FEATURED_DESTINATIONS_DATA)

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve place details by place ID.
        """
        if place_id in _PLACES_STORE:
            p = _PLACES_STORE[place_id]
            nearby = [
                other for other in _PLACES_STORE.values()
                if other["id"] != place_id and abs(other["lat"] - p["lat"]) < 0.08 and abs(other["lon"] - p["lon"]) < 0.08
            ][:4]
            return {"place": p, "nearby_places": nearby}

        # If not in cache, resolve from place_id format osm_{type}_{id}
        parts = place_id.split("_")
        if len(parts) == 3 and parts[0] == "osm":
            el_type, el_id = parts[1], parts[2]
            try:
                import httpx
                query = f"[out:json][timeout:6];{el_type}({el_id});out center tags;"
                async with httpx.AsyncClient(timeout=6.0) as client:
                    for ep in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
                        res = await client.post(ep, data={"data": query}, headers={"User-Agent": "TravelTrack-Explore/3.0"})
                        if res.status_code == 200:
                            data = res.json().get("elements", [])
                            if data:
                                el = data[0]
                                tags = el.get("tags", {})
                                name = tags.get("name") or tags.get("name:en") or "Place"
                                p_lat = el.get("lat") or el.get("center", {}).get("lat") or 0.0
                                p_lon = el.get("lon") or el.get("center", {}).get("lon") or 0.0
                                raw_p = {
                                    "id": place_id,
                                    "provider_id": f"{el_type}/{el_id}",
                                    "name": name,
                                    "category": self.overpass._map_osm_category(tags),
                                    "address": self.overpass._format_address(tags, name),
                                    "lat": float(p_lat),
                                    "lon": float(p_lon),
                                    "osm_wikipedia": tags.get("wikipedia"),
                                    "osm_wikidata": tags.get("wikidata"),
                                    "osm_image": tags.get("image"),
                                    "tags": []
                                }
                                norm = await self._enrich_place(raw_p, name)
                                return {"place": norm, "nearby_places": []}
            except Exception:
                pass

        return None


# Singleton instance
explore_provider = ExploreProvider()
