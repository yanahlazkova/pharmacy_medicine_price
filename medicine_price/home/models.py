from django.db import models


class SearchResult(models.Model):

    class StockStatus(models.TextChoices):
        IN_STOCK = "in_stock", "Є"
        OUT_OF_STOCK = "out_of_stock", "Немає"
        UNKNOWN = "unknown", "Невідомо"

    # що шукали
    query = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Пошуковий запит"
    )

    # ключ сесії, щоб користувачі бачили тільки свої результати пошуку
    session_key = models.CharField(
        max_length=40,
        db_index=True
    )

    # назва препарату
    name = models.CharField(
        max_length=500,
        db_index=True,
        verbose_name="Назва препарату"
    )

    # назва препарату для пошуку
    nameNormalized = models.CharField(
        max_length=500,
        db_index=True,
    )

    # id препарата
    product_id = models.IntegerField()

    # аптека
    pharmacy = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Аптека"
    )

    # ціна
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Ціна"
    )

    # alias / slug / url
    alias = models.URLField(
        max_length=1000,
        verbose_name="Посилання",
    )

    # бренд
    brand = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="Бренд"
    )

    # картинка
    # image_url = models.URLField(
    #     max_length=1000,
    #     blank=True,
    #     verbose_name="Картинка"
    # )

    # наявність
    stock_status = models.CharField(
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.UNKNOWN,
        db_index=True,
        verbose_name="Наявність"
    )

    # дата створення
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ["price"]

        indexes = [
            models.Index(fields=["query"]),
            models.Index(fields=["pharmacy"]),
            models.Index(fields=["price"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["stock_status"]),
        ]

        verbose_name = "Результат пошуку"
        verbose_name_plural = "Результати пошуку"

    def __str__(self):
        return f"{self.name} | {self.pharmacy} | {self.price}"
