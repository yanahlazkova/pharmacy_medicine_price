
from django.db import models


class CategoryApteka911(models.Model):
    url = models.URLField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Категорія')
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.url


class DrugApteka911(models.Model):
    productID = models.IntegerField(unique=True)
    productNameNormalized = models.CharField(
        max_length=255,
        db_index=True,
        default='',
    )
    category = models.URLField(verbose_name='url категорії', blank=True, null=True)
    productName = models.CharField(max_length=255, verbose_name="Назва препарату")
    alias = models.CharField(max_length=255, blank=True, null=True)
    brandName = models.CharField(max_length=255, blank=True, null=True)
    formName = models.CharField(max_length=255, blank=True, null=True)
    productAvail = models.BooleanField(default=True, verbose_name="Доступність")
    productCountry = models.CharField(max_length=255, blank=True, null=True)
    productForm = models.CharField(max_length=255, verbose_name="Форма випуску", blank=True, null=True)
    productMeasure = models.CharField(max_length=255, blank=True, null=True)
    productMname = models.CharField(max_length=255, blank=True, null=True)
    productPrice = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна, від")
    img = models.CharField(max_length=255, blank=True, null=True)
    time_created = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')  # дата при створенні запису
    time_updated = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')  # дата при зміні запису

    def __str__(self):
        return self.productName or self.alias