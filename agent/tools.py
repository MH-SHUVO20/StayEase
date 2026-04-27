"""Tool definitions for the StayEase booking agent."""

from datetime import date
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agent.db import execute_one, fetch_all, fetch_one


MOCK_LISTINGS = [
    {
        "listing_id": "LST-001",
        "title": "Sea Breeze Villa",
        "description": "Beachfront villa in Cox's Bazar with sea views and modern amenities.",
        "location": "Cox's Bazar",
        "price_per_night": 4500,
        "currency": "BDT",
        "max_guests": 4,
        "bedrooms": 2,
        "bathrooms": 1,
        "amenities": ["Wi-Fi", "AC", "Kitchen", "Beach Access", "Parking"],
        "rating": 4.8,
        "total_reviews": 124,
        "host_name": "Rahim Uddin",
        "cancellation_policy": "Free cancellation up to 48 hours before check-in",
    },
    {
        "listing_id": "LST-002",
        "title": "Ocean View Resort",
        "description": "Family-friendly resort close to the beach in Cox's Bazar.",
        "location": "Cox's Bazar",
        "price_per_night": 6200,
        "currency": "BDT",
        "max_guests": 6,
        "bedrooms": 3,
        "bathrooms": 2,
        "amenities": ["Wi-Fi", "AC", "Breakfast", "Pool", "Parking"],
        "rating": 4.5,
        "total_reviews": 89,
        "host_name": "Tanzim Hasan",
        "cancellation_policy": "Free cancellation up to 24 hours before check-in",
    },
]


class SearchInput(BaseModel):
    """Input for searching available properties."""

    location: str = Field(..., description="City or area in Bangladesh, e.g. Cox's Bazar")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(..., ge=1, description="Number of guests")


class DetailsInput(BaseModel):
    """Input for getting listing details."""

    listing_id: str = Field(..., description="Unique listing ID")


class BookingInput(BaseModel):
    """Input for creating a booking."""

    listing_id: str = Field(..., description="Listing to book")
    guest_name: str = Field(..., description="Full name of the guest")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(..., ge=1, description="Number of guests")


def _public_listing(row: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields the guest should see in search results."""
    return {
        "listing_id": row["listing_id"],
        "title": row["title"],
        "location": row["location"],
        "price_per_night": row["price_per_night"],
        "currency": row.get("currency", "BDT"),
        "max_guests": row["max_guests"],
        "rating": row.get("rating"),
    }


def _mock_search(location: str, guests: int) -> list[dict[str, Any]]:
    """Return mock listings when PostgreSQL is unavailable."""
    return [
        _public_listing(listing)
        for listing in MOCK_LISTINGS
        if listing["location"].lower() == location.lower()
        and listing["max_guests"] >= guests
    ]


def _booking_nights(booking: BookingInput) -> int:
    """Calculate how many nights the guest wants to stay."""
    return (booking.check_out - booking.check_in).days


def _create_booking_query() -> str:
    """Return the SQL query used to create a booking."""
    return """
        WITH selected_listing AS (
            SELECT id, price_per_night
            FROM listings
            WHERE id = %s
              AND is_active = true
              AND max_guests >= %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM bookings AS b
                  WHERE b.listing_id = listings.id
                    AND b.status IN ('confirmed', 'pending')
                    AND b.check_in < %s
                    AND b.check_out > %s
              )
            LIMIT 1
        )
        INSERT INTO bookings (
            id,
            listing_id,
            guest_name,
            check_in,
            check_out,
            guests,
            total_price,
            status
        )
        SELECT
            'BKG-' || to_char(now(), 'YYYYMMDDHH24MISSMS'),
            id,
            %s,
            %s,
            %s,
            %s,
            price_per_night * %s,
            'confirmed'
        FROM selected_listing
        RETURNING
            id AS booking_id,
            listing_id,
            guest_name,
            check_in,
            check_out,
            guests,
            total_price,
            status;
    """


def _booking_params(booking: BookingInput, nights: int) -> tuple[Any, ...]:
    """Prepare the SQL parameters for creating a booking."""
    return (
        booking.listing_id,
        booking.guests,
        booking.check_out,
        booking.check_in,
        booking.guest_name,
        booking.check_in,
        booking.check_out,
        booking.guests,
        nights,
    )


def _try_create_booking_in_db(
    booking: BookingInput,
    nights: int,
) -> dict[str, Any] | None:
    """Try to create the booking in PostgreSQL."""
    created = execute_one(_create_booking_query(), _booking_params(booking, nights))
    if not created:
        return None

    created["nights"] = nights
    created["currency"] = "BDT"
    return created


def _mock_booking_response(booking: BookingInput, nights: int) -> dict[str, Any]:
    """Return a demo booking when PostgreSQL is unavailable."""
    price_per_night = 4500
    return {
        "booking_id": "BKG-MOCK-001",
        "listing_id": booking.listing_id,
        "guest_name": booking.guest_name,
        "check_in": booking.check_in.isoformat(),
        "check_out": booking.check_out.isoformat(),
        "guests": booking.guests,
        "nights": nights,
        "price_per_night": price_per_night,
        "total_price": nights * price_per_night,
        "currency": "BDT",
        "status": "confirmed_mock",
    }


@tool("search_available_properties", args_schema=SearchInput)
def search_available_properties(
    location: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> list[dict[str, Any]]:
    """Search for available properties in a given location and date range."""
    query = """
        SELECT
            l.id AS listing_id,
            l.title,
            l.location,
            l.price_per_night,
            'BDT' AS currency,
            l.max_guests,
            l.rating
        FROM listings AS l
        WHERE lower(l.location) = lower(%s)
          AND l.max_guests >= %s
          AND l.is_active = true
          AND NOT EXISTS (
              SELECT 1
              FROM bookings AS b
              WHERE b.listing_id = l.id
                AND b.status IN ('confirmed', 'pending')
                AND b.check_in < %s
                AND b.check_out > %s
          )
        ORDER BY l.price_per_night ASC, l.rating DESC NULLS LAST
        LIMIT 10;
    """

    try:
        return fetch_all(query, (location, guests, check_out, check_in))
    except Exception:
        return _mock_search(location, guests)


@tool("get_listing_details", args_schema=DetailsInput)
def get_listing_details(listing_id: str) -> dict[str, Any]:
    """Get full details for a specific property listing."""
    query = """
        SELECT
            id AS listing_id,
            title,
            description,
            location,
            price_per_night,
            'BDT' AS currency,
            max_guests,
            bedrooms,
            bathrooms,
            amenities,
            rating,
            total_reviews,
            host_name,
            cancellation_policy
        FROM listings
        WHERE id = %s
          AND is_active = true
        LIMIT 1;
    """

    try:
        listing = fetch_one(query, (listing_id,))
        if listing:
            return listing
    except Exception:
        pass

    for listing in MOCK_LISTINGS:
        if listing["listing_id"] == listing_id:
            return listing

    return {"error": "Listing not found.", "listing_id": listing_id}


@tool("create_booking", args_schema=BookingInput)
def create_booking(**booking_data: Any) -> dict[str, Any]:
    """Create a booking for a property after the guest confirms."""
    booking = BookingInput(**booking_data)
    nights = _booking_nights(booking)
    if nights <= 0:
        return {"error": "Check-out date must be after check-in date."}

    try:
        created = _try_create_booking_in_db(booking, nights)
        if created:
            return created
    except Exception:
        pass

    return _mock_booking_response(booking, nights)


ALL_TOOLS = [search_available_properties, get_listing_details, create_booking]
