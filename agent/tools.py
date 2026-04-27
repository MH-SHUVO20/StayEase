"""Tool definitions for the StayEase booking agent."""

from datetime import date
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


# Input schemas
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


# Tools
@tool("search_available_properties", args_schema=SearchInput)
def search_available_properties(
    location: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> list[dict[str, Any]]:
    """Search for available properties in a given location and date range.

    Called when the guest wants to find a place to stay.
    """
    # TODO: query the listings table and exclude already-booked dates
    return [
        {
            "listing_id": "LST-001",
            "title": "Sea Breeze Villa",
            "location": location,
            "price_per_night": 4500,
            "currency": "BDT",
            "max_guests": 4,
            "rating": 4.8,
        },
        {
            "listing_id": "LST-002",
            "title": "Ocean View Resort",
            "location": location,
            "price_per_night": 6200,
            "currency": "BDT",
            "max_guests": 6,
            "rating": 4.5,
        },
    ]


@tool("get_listing_details", args_schema=DetailsInput)
def get_listing_details(listing_id: str) -> dict[str, Any]:
    """Get full details for a specific property listing.

    Called when the guest asks about a particular property.
    """
    # TODO: query the listings table by id
    return {
        "listing_id": listing_id,
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
    }


@tool("create_booking", args_schema=BookingInput)
def create_booking(
    **booking_data: Any,
) -> dict[str, Any]:
    """Create a booking for a property.

    Called only after the guest confirms they want to book.
    """
    booking = BookingInput(**booking_data)

    # TODO: insert into bookings table
    nights = (booking.check_out - booking.check_in).days
    price_per_night = 4500  # would come from DB
    total_price = nights * price_per_night

    return {
        "booking_id": "BKG-20260427-001",
        "listing_id": booking.listing_id,
        "guest_name": booking.guest_name,
        "check_in": booking.check_in.isoformat(),
        "check_out": booking.check_out.isoformat(),
        "guests": booking.guests,
        "nights": nights,
        "price_per_night": price_per_night,
        "total_price": total_price,
        "currency": "BDT",
        "status": "confirmed",
    }


# All tools for binding to the LLM
ALL_TOOLS = [search_available_properties, get_listing_details, create_booking]
