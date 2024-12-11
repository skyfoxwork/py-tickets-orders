from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Ticket, Order


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class CinemaHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieListSerializer(MovieSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )


class MovieDetailSerializer(MovieSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class MovieSessionListSerializer(MovieSessionSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity", read_only=True
    )

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "cinema_hall_name",
            "cinema_hall_capacity",
        )


class MovieSessionDetailSerializer(MovieSessionSerializer):
    movie = MovieListSerializer(many=False, read_only=True)
    cinema_hall = CinemaHallSerializer(many=False, read_only=True)

    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class TicketSerializer(serializers.ModelSerializer):
    movie_session = MovieSessionListSerializer(many=False, read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "movie_session")

    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs)
        Ticket.validate_rows_seats(
            attrs["row"],
            attrs["seat"],
            attrs["movie_session"],
            serializers.ValidationError
        )
        return data
        # for ticket_attr_value, ticket_attr_name, cinema_hall_attr_name in [
        #     (attrs["row"], "row", "rows"),
        #     (attrs["seat"], "seat", "seats_in_row"),
        # ]:
        #     count_attrs = getattr(
        #         attrs["movie_session"].cinema_hall, cinema_hall_attr_name
        #     )
        #     if not (1 <= ticket_attr_value <= count_attrs):
        #         raise serializers.ValidationError(
        #             {
        #                 ticket_attr_name: f"{ticket_attr_name} "
        #                 f"number must be in available range: "
        #                 f"(1, {cinema_hall_attr_name}): "
        #                 f"(1, {count_attrs})"
        #             }
        #         )



# class UserSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = get_user_model()
#         fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order
