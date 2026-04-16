
# Scraper Configuration File
# Set 'enabled': True for categories you want to scrape
# Set 'enabled': False for categories you want to skip

import os

URL_CONFIG = {
    # Winter Collection
    "Winter_Men": {
        "url": "https://charcoal.com.pk/collections/shalwar-kameez?page=2",
        "folder": os.path.join("data", "Winter", "Men"),
        "enabled": True,
        # Site-specific selectors and scraping hints for Charcoal Shalwar Kameez
        "selectors": {
            # Element that indicates the product grid is present/ready
            "page_ready": ".product-card__figure, .product-card__image",
            # CSS selector to get product tiles/cards
            "product_cards": ".product-card__figure",
            # CSS selector to get image elements - target images within product cards
            "image_elements": ".product-card__figure img, .product-card__image",
            # Links that wrap entire product
            "product_link": "a[href*='/products/']",
            # Preferred attribute order - Charcoal uses srcset and src
            "attr_priority": ["srcset", "src", "data-src", "data-srcset"],
            # Filter to include Charcoal CDN and product images
            "url_includes": ["charcoal.com.pk", "cdn.shopify.com"],
            # Exclude tiny placeholders, icons, or non-product images
            "url_excludes": ["placeholder", ".svg", "icon", "logo", "banner", "loading", "arrow", "nav"],
        }
    },
    "Winter_Women": {
        "url": "https://zellbury.com/collections/winter-collection",
        "folder": os.path.join("data", "Winter", "Women"),
        "enabled": False,
        # Site-specific selectors and scraping hints for Zellbury
        "selectors": {
            # Element that indicates the product grid is present/ready
            "page_ready": ".swiper-slide, .media-image",
            # CSS selector to get product tiles/cards
            "product_cards": ".swiper-slide",
            # CSS selector to get image elements - target images within swiper slides
            "image_elements": ".swiper-slide img, .media-image",
            # Links that wrap entire product
            "product_link": "a[href*='/products/']",
            # Preferred attribute order - Zellbury uses srcset and Shopify CDN
            "attr_priority": ["srcset", "src", "data-src", "data-srcset"],
            # Filter to include Zellbury CDN and product images
            "url_includes": ["zellbury.com", "cdn.shopify.com"],
            # Exclude tiny placeholders, icons, or non-product images
            "url_excludes": ["placeholder", ".svg", "icon", "logo", "banner", "loading", "arrow", "nav"],
        }
    },
    
    # Summer Collection
    "Summer_Men": {
        "url": "https://laam.pk/nodes/men-kurta-531",
        "folder": os.path.join("data", "Summer", "Men"),
        "enabled": False,
        # Site-specific selectors and scraping hints for Laam.pk
        "selectors": {
            # Element that indicates the product grid is present/ready
            "page_ready": ".image-box, .lazy_image, img[srcset]",
            # CSS selector to get product tiles/cards
            "product_cards": ".image-box, .product-item, .grid-item",
            # CSS selector to get image elements - target images in image-box containers and lazy images
            "image_elements": ".image-box img, .lazy_image, img[srcset], img",
            # Links that wrap entire product
            "product_link": "a[href*='/products/'], a[href*='/nodes/']",
            # Preferred attribute order - Laam.pk uses srcset and Shopify CDN
            "attr_priority": ["srcset", "src", "data-src", "data-srcset"],
            # Filter to include Shopify CDN images used by Laam.pk
            "url_includes": ["cdn.shopify.com", "laam.pk"],
            # Exclude tiny placeholders, icons, or non-product images
            "url_excludes": ["placeholder", ".svg", "icon", "logo", "banner", "loading", "arrow", "nav"],
        }
    },
    "Summer_Women": {
        "url": "https://beechtree.pk/collections/unstitched",
        "folder": os.path.join("data", "Summer", "Women"),
        "enabled": False,
        # Site-specific selectors and scraping hints for Beechtree
        "selectors": {
            # Element that indicates the product grid is present/ready
            "page_ready": ".media, .media--transparent",
            # CSS selector to get product tiles/cards
            "product_cards": ".media",
            # CSS selector to get image elements - target images within media containers
            "image_elements": ".media img, .media--transparent img",
            # Links that wrap entire product
            "product_link": "a[href*='/products/']",
            # Preferred attribute order - Beechtree uses srcset and Shopify CDN
            "attr_priority": ["srcset", "src", "data-src", "data-srcset"],
            # Filter to include Beechtree CDN and product images
            "url_includes": ["beechtree.pk", "cdn.shopify.com"],
            # Exclude tiny placeholders, icons, or non-product images
            "url_excludes": ["placeholder", ".svg", "icon", "logo", "banner", "loading", "arrow", "nav"],
        }
    }
}
