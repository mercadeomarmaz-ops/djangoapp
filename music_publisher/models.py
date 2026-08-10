"""Concrete models and CWR generation logic."""

import base64
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.template import Context
from django.urls import reverse
from django.utils import timezone
from django.utils.duration import duration_string

from .base import (
    ArtistBase,
    IPIBase,
    LabelBase,
    LibraryBase,
    PersonBase,
    ReleaseBase,
    TitleBase,
    WriterBase,
    upload_to,
)
from .cwr_templates import (
    TEMPLATES_21,
    TEMPLATES_22,
    TEMPLATES_30,
    TEMPLATES_31,
)
from .societies import SOCIETIES, SOCIETY_DICT
from .validators import CWRFieldValidator

WORLD_DICT = {"tis-a": "2WL", "tis-n": "2136", "name": "World"}


class Artist(ArtistBase):
    """Performing artist."""

    class Meta:
        ordering = ("last_name", "first_name", "isni", "-id")

    def get_dict(self):
        return {
            "id": self.id,
            "code": self.artist_id,
            "last_name": self.last_name,
            "first_name": self.first_name or None,
            "isni": self.isni or None,
        }

    @property
    def artist_id(self):
        return "A{:06d}".format(self.id) if self.id else ""


class Label(LabelBase):
    """Music Label."""

    class Meta:
        verbose_name = "Music Label"
        ordering = ("name", "-id")

    def __str__(self):
        return self.name.upper()

    @property
    def label_id(self):
        return "LA{:06d}".format(self.id) if self.id else ""

    def get_dict(self):
        return {"id": self.id, "code": self.label_id, "name": self.name}


class Library(LibraryBase):
    """Music Library."""

    class Meta:
        verbose_name = "Music Library"
        verbose_name_plural = "Music Libraries"
        ordering = ("name",)

    def __str__(self):
        return self.name.upper()

    @property
    def library_id(self):
        return "LI{:06d}".format(self.id) if self.id else ""

    def get_dict(self):
        return {"id": self.id, "code": self.library_id, "name": self.name}


class Release(ReleaseBase):
    """Music Release."""

    class Meta:
        verbose_name = "Release"

    library = models.ForeignKey(
        Library, null=True, blank=True, on_delete=models.PROTECT
    )
    release_label = models.ForeignKey(
        Label,
        verbose_name="Release (album) label",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    artist = models.ForeignKey(
        Artist,
        verbose_name="Display Artist",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Leave empty if a compilation by different artists.",
    )
    recordings = models.ManyToManyField("Recording", through="Track")

    def __str__(self):
        if self.cd_identifier:
            if self.release_title:
                return "{}: {} ({})".format(
                    self.cd_identifier, self.release_title.upper(), self.library
                )
            return "{} ({})".format(self.cd_identifier, self.library)
        if self.release_label:
            return "{} ({})".format(
                (self.release_title or "<no title>").upper(),
                self.release_label,
            )
        return (self.release_title or "<no title>").upper()

    @property
    def release_id(self):
        return "RE{:06d}".format(self.id) if self.id else ""

    def get_dict(self, with_tracks=False):
        title = self.release_title or None
        date = self.release_date.strftime("%Y%m%d") if self.release_date else None
        label = self.release_label.get_dict() if self.release_label else None
        artist = self.artist.get_dict() if self.artist else None
        data = {
            "id": self.id,
            "code": self.release_id,
            "title": title,
            "date": date,
            "label": label,
            "artist": artist,
            "ean": self.ean,
        }
        if with_tracks:
            data["tracks"] = [track.get_dict() for track in self.tracks.all()]
        return data


class LibraryReleaseManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(cd_identifier__isnull=False, library__isnull=False)
        )

    def get_dict(self, qs):
        return {"releases": [release.get_dict(with_tracks=True) for release in qs]}


class LibraryRelease(Release):
    class Meta:
        proxy = True
        verbose_name = "Library Release"
        verbose_name_plural = "Library Releases"

    objects = LibraryReleaseManager()

    def clean(self):
        title_required = self.ean or self.release_date or self.release_label
        if title_required and not self.release_title:
            raise ValidationError({"release_title": "Required if other release data is set."})
        return super().clean()

    def get_origin_dict(self):
        return {
            "origin_type": {"code": "LIB", "name": "Library Work"},
            "cd_identifier": self.cd_identifier,
            "library": self.library.get_dict(),
        }


class CommercialReleaseManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(cd_identifier__isnull=True, library__isnull=True)
        )

    def get_dict(self, qs):
        return {"releases": [release.get_dict(with_tracks=True) for release in qs]}


class CommercialRelease(Release):
    class Meta:
        proxy = True
        verbose_name = "Commercial Release"
        verbose_name_plural = "Commercial Releases"

    objects = CommercialReleaseManager()


class PlaylistManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(cd_identifier__isnull=False, library__isnull=True)
        )

    def get_dict(self, qs):
        return {"releases": [release.get_dict(with_tracks=True) for release in qs]}


class Playlist(Release):
    class Meta:
        proxy = True
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"

    objects = PlaylistManager()

    def __str__(self):
        return self.release_title or ""

    def clean(self, *args, **kwargs):
        if self.cd_identifier is None:
            self.cd_identifier = base64.urlsafe_b64encode(uuid.uuid4().bytes)
            self.cd_identifier = self.cd_identifier.decode().rstrip("=")[:15]
        return super().clean(*args, **kwargs)

    @property
    def secret_url(self):
        return reverse("secret_playlist", args=[self.cd_identifier])

    @property
    def secret_api_url(self):
        return reverse("playlist-detail", args=[self.cd_identifier])


class Writer(WriterBase):
    """Writers."""

    class Meta:
        ordering = ("last_name", "first_name", "ipi_name", "-id")
        verbose_name = "Writer"
        verbose_name_plural = "Writers"

    def __str__(self):
        name = super().__str__()
        if self.generally_controlled:
            return name + " (*)"
        return name

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.pk is None or self._can_be_controlled:
            return
        if self.writerinwork_set.filter(controlled=True).exists():
            raise ValidationError(
                "This writer is controlled in at least one work. "
                + "Required fields are: Last name, IPI name and PR society. "
                + 'See "Writers" in the user manual.'
            )

    @property
    def writer_id(self):
        return "W{:06d}".format(self.id) if self.id else ""

    def get_dict(self):
        data = {
            "id": self.id,
            "code": self.writer_id,
            "first_name": self.first_name or None,
            "last_name": self.last_name or None,
            "ipi_name_number": self.ipi_name or None,
            "ipi_base_number": self.ipi_base or None,
            "account_number": self.account_number,
            "affiliations": [],
        }
        if self.pr_society:
            data["affiliations"].append(
                {
                    "organization": {
                        "code": self.pr_society,
                        "name": SOCIETY_DICT.get(self.pr_society, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "PR", "name": "Performance Rights"},
                    "territory": WORLD_DICT,
                }
            )
        if self.mr_society:
            data["affiliations"].append(
                {
                    "organization": {
                        "code": self.mr_society,
                        "name": SOCIETY_DICT.get(self.mr_society, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "MR", "name": "Mechanical Rights"},
                    "territory": WORLD_DICT,
                }
            )
        if self.sr_society:
            data["affiliations"].append(
                {
                    "organization": {
                        "code": self.sr_society,
                        "name": SOCIETY_DICT.get(self.sr_society, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "SR", "name": "Synchronization Rights"},
                    "territory": WORLD_DICT,
                }
            )
        return data


class WorkManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("writers")

    def get_dict_items(self, qs):
        qs = qs.prefetch_related("alternatetitle_set")
        qs = qs.prefetch_related("writerinwork_set__writer")
        qs = qs.prefetch_related("artistinwork_set__artist")
        qs = qs.prefetch_related("library_release__library")
        qs = qs.prefetch_related("recordings__record_label")
        qs = qs.prefetch_related("recordings__artist")
        qs = qs.prefetch_related("recordings__tracks__release__library")
        qs = qs.prefetch_related("recordings__tracks__release__release_label")
        qs = qs.prefetch_related("workacknowledgement_set")
        for work in qs:
            yield work.get_dict()

    def get_dict(self, qs):
        return {"works": list(self.get_dict_items(qs))}


class Work(TitleBase):
    """Musical work."""

    class Meta:
        verbose_name = "Musical Work"
        ordering = ("-id",)
        permissions = (("can_process_royalties", "Can perform royalty calculations"),)

    @staticmethod
    def persist_work_ids(qs):
        qs = qs.prefetch_related("recordings")
        for work in qs.filter(_work_id__isnull=True):
            work.work_id = work.work_id
            work.save()
            for rec in work.recordings.all():
                if rec._recording_id is None:
                    rec.recording_id = rec.recording_id
                    rec.save()

    _work_id = models.CharField(
        "Work ID",
        max_length=14,
        blank=True,
        null=True,
        unique=True,
        editable=False,
        validators=(CWRFieldValidator("name"),),
    )
    iswc = models.CharField(
        "ISWC",
        max_length=15,
        blank=True,
        null=True,
        unique=True,
        validators=(CWRFieldValidator("iswc"),),
    )
    original_title = models.CharField(
        verbose_name="Title of original work",
        max_length=60,
        db_index=True,
        blank=True,
        help_text="Use only for modification of existing works.",
        validators=(CWRFieldValidator("title"),),
    )
    library_release = models.ForeignKey(
        "LibraryRelease",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="works",
        verbose_name="Library release",
    )
    last_change = models.DateTimeField("Last Edited", editable=False, null=True)
    artists = models.ManyToManyField("Artist", through="ArtistInWork")
    writers = models.ManyToManyField("Writer", through="WriterInWork", related_name="works")

    objects = WorkManager()

    @property
    def work_id(self):
        if self._work_id:
            return self._work_id
        if self.id is None:
            return ""
        return "{}{:06}".format(settings.PUBLISHER_CODE, self.id)

    @work_id.setter
    def work_id(self, value):
        if self._work_id is not None:
            raise NotImplementedError("work_id can not be changed")
        if value:
            self._work_id = value

    def is_modification(self):
        return bool(self.original_title)

    def clean_fields(self, *args, **kwargs):
        if self.iswc:
            self.iswc = self.iswc.replace("-", "").replace(".", "")
        return super().clean_fields(*args, **kwargs)

    def writer_last_names(self):
        writers = sorted(set(self.writers.all()), key=lambda w: w.last_name)
        return " / ".join(w.last_name.upper() for w in writers)

    def __str__(self):
        return "{}: {} ({})".format(
            self.work_id, self.title.upper(), self.writer_last_names()
        )

    @staticmethod
    def get_publisher_dict():
        data = {
            "id": 1,
            "code": settings.PUBLISHER_CODE,
            "name": settings.PUBLISHER_NAME,
            "ipi_name_number": settings.PUBLISHER_IPI_NAME,
            "ipi_base_number": settings.PUBLISHER_IPI_BASE,
            "affiliations": [
                {
                    "organization": {
                        "code": settings.PUBLISHER_SOCIETY_PR,
                        "name": SOCIETY_DICT.get(settings.PUBLISHER_SOCIETY_PR, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "PR", "name": "Performance Rights"},
                    "territory": WORLD_DICT,
                }
            ],
        }
        if settings.PUBLISHER_SOCIETY_MR:
            data["affiliations"].append(
                {
                    "organization": {
                        "code": settings.PUBLISHER_SOCIETY_MR,
                        "name": SOCIETY_DICT.get(settings.PUBLISHER_SOCIETY_MR, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "MR", "name": "Mechanical Rights"},
                    "territory": WORLD_DICT,
                }
            )
        if settings.PUBLISHER_SOCIETY_SR:
            data["affiliations"].append(
                {
                    "organization": {
                        "code": settings.PUBLISHER_SOCIETY_SR,
                        "name": SOCIETY_DICT.get(settings.PUBLISHER_SOCIETY_SR, "").split(",")[0],
                    },
                    "affiliation_type": {"code": "SR", "name": "Synchronization Rights"},
                    "territory": WORLD_DICT,
                }
            )
        return data

    def get_dict(self, with_recordings=True):
        data = {
            "id": self.id,
            "code": self.work_id,
            "work_title": self.title,
            "last_change": self.last_change,
            "version_type": (
                {"code": "MOD", "name": "Modified Version of a musical work"}
                if self.original_title
                else {"code": "ORI", "name": "Original Work"}
            ),
            "iswc": self.iswc,
            "other_titles": [at.get_dict() for at in self.alternatetitle_set.all()],
            "origin": self.library_release.get_origin_dict() if self.library_release else None,
            "writers": [],
            "performing_artists": [],
            "original_works": [],
            "cross_references": [],
        }
        if self.original_title:
            data["original_works"].append({"work_title": self.original_title})
        for aiw in self.artistinwork_set.all():
            data["performing_artists"].append(aiw.get_dict())
        for wiw in self.writerinwork_set.all():
            data["writers"].append(wiw.get_dict())
        if with_recordings:
            data["recordings"] = [
                recording.get_dict(with_releases=True, with_work=False)
                for recording in self.recordings.all()
            ]
        for ack in self.workacknowledgement_set.all():
            if ack.remote_work_id:
                data["cross_references"].append(ack.get_dict())
        return data


class AlternateTitle(TitleBase):
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    suffix = models.BooleanField(
        default=False,
        help_text="Select if this title is only a suffix to the main title.",
    )

    class Meta:
        indexes = [models.Index(fields=["work_id", "title_type", "title"])]
        ordering = ("-suffix", "title_type", "title")
        verbose_name = "Alternate Title"

    def get_dict(self):
        return {
            "title": str(self),
            "title_type": {"code": self.title_type, "name": self.get_title_type_display()},
        }

    def __str__(self):
        if self.suffix:
            return "{} {}".format(self.work.title, self.title)
        return super().__str__()


class ArtistInWork(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Artist performing"
        verbose_name_plural = "Artists performing (not mentioned in recordings section)"
        indexes = [models.Index(fields=["work", "artist"])]
        ordering = ("artist__last_name", "artist__first_name")

    def __str__(self):
        return str(self.artist)

    def get_dict(self):
        return {"artist": self.artist.get_dict()}


class WriterInWork(models.Model):
    class Meta:
        verbose_name = "Writer in Work"
        verbose_name_plural = "Writers in Work"
        indexes = [models.Index(fields=["work", "writer", "controlled"])]
        ordering = ("-controlled", "writer__last_name", "writer__first_name", "-id")

    ROLES = (
        ("CA", "Composer&Lyricist"),
        ("C ", "Composer"),
        ("A ", "Lyricist"),
        ("AR", "Arranger"),
        ("AD", "Adaptor"),
        ("TR", "Translator"),
    )

    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    writer = models.ForeignKey(Writer, on_delete=models.PROTECT, blank=True, null=True)
    saan = models.CharField(
        "Society-assigned specific agreement number",
        max_length=14,
        blank=True,
        null=True,
        validators=(CWRFieldValidator("saan"),),
    )
    controlled = models.BooleanField(default=False)
    relative_share = models.DecimalField("Manuscript share", max_digits=5, decimal_places=2)
    capacity = models.CharField("Role", max_length=2, blank=True, choices=ROLES)
    publisher_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of royalties kept by the publisher,\nin a specific agreement.",
    )

    def __str__(self):
        return str(self.writer)

    def clean_fields(self, *args, **kwargs):
        if self.saan:
            self.saan = self.saan.upper()
        return super().clean_fields(*args, **kwargs)

    def clean(self):
        generally_controlled = self.writer and self.writer.generally_controlled
        if generally_controlled and not self.controlled:
            raise ValidationError({"controlled": "Must be set for a generally controlled writer."})
        errors = {}
        if self.controlled:
            if not self.capacity:
                errors["capacity"] = "Must be set for a controlled writer."
            if not self.writer:
                errors["writer"] = "Must be set for a controlled writer."
            elif not self.writer._can_be_controlled:
                errors["writer"] = 'IPI name and PR society must be set. See "Writers" in the user manual'
        else:
            if self.saan:
                errors["saan"] = "Must be empty if writer is not controlled."
            if self.publisher_fee:
                errors["publisher_fee"] = "Must be empty if writer is not controlled."
        if errors:
            raise ValidationError(errors)

    def get_agreement_dict(self):
        if not self.controlled or not self.writer:
            return None
        pub_pr_soc = settings.PUBLISHER_SOCIETY_PR
        pub_pr_name = SOCIETY_DICT.get(pub_pr_soc, "").split(",")[0]
        if self.writer.generally_controlled and not self.saan:
            return {
                "recipient_organization": {"code": pub_pr_soc, "name": pub_pr_name},
                "recipient_agreement_number": self.writer.saan,
                "agreement_type": {"code": "OG", "name": "Original General"},
            }
        return {
            "recipient_organization": {"code": pub_pr_soc},
            "recipient_agreement_number": self.saan,
            "agreement_type": {"code": "OS", "name": "Original Specific"},
        }

    def get_dict(self):
        writer = self.writer.get_dict() if self.writer else None
        role = (
            {"code": self.capacity.strip(), "name": self.get_capacity_display()}
            if self.capacity
            else None
        )
        ops = []
        if self.controlled:
            ops.append(
                {
                    "publisher": self.work.get_publisher_dict(),
                    "publisher_role": {"code": "E", "name": "Original publisher"},
                    "agreement": self.get_agreement_dict(),
                }
            )
        return {
            "writer": writer,
            "controlled": self.controlled,
            "relative_share": str(self.relative_share / 100),
            "writer_role": role,
            "original_publishers": ops,
        }


class Recording(models.Model):
    class Meta:
        verbose_name = "Recording"
        verbose_name_plural = "Recordings"
        ordering = ("-id",)

    _recording_id = models.CharField(
        "Recording ID",
        max_length=14,
        blank=True,
        null=True,
        unique=True,
        editable=False,
        validators=(CWRFieldValidator("name"),),
    )
    recording_title = models.CharField(blank=True, max_length=60, validators=(CWRFieldValidator("title"),))
    recording_title_suffix = models.BooleanField(default=False, help_text="A suffix to the WORK title.")
    version_title = models.CharField(blank=True, max_length=60, validators=(CWRFieldValidator("title"),))
    version_title_suffix = models.BooleanField(default=False, help_text="A suffix to the RECORDING title.")
    release_date = models.DateField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    isrc = models.CharField("ISRC", max_length=15, blank=True, null=True, unique=True, validators=(CWRFieldValidator("isrc"),))
    record_label = models.ForeignKey(Label, verbose_name="Record label", null=True, blank=True, on_delete=models.PROTECT)
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="recordings")
    artist = models.ForeignKey(Artist, verbose_name="Recording Artist", related_name="recordings", on_delete=models.PROTECT, blank=True, null=True)
    releases = models.ManyToManyField(Release, through="Track")
    audio_file = models.FileField(upload_to=upload_to, max_length=255, blank=True)

    def clean_fields(self, *args, **kwargs):
        empty = not any([
            self.recording_title,
            self.version_title,
            self.release_date,
            self.isrc,
            self.duration,
            self.record_label,
            self.artist,
            self.audio_file,
        ])
        if empty:
            raise ValidationError("No data left, please delete instead.")
        if self.isrc:
            self.isrc = self.isrc.replace("-", "").replace(".", "")
        return super().clean_fields(*args, **kwargs)

    @property
    def complete_recording_title(self):
        if self.recording_title_suffix:
            return "{} {}".format(self.work.title, self.recording_title).strip()
        return self.recording_title

    @property
    def complete_version_title(self):
        if self.version_title_suffix:
            return "{} {}".format(self.complete_recording_title or self.work.title, self.version_title).strip()
        return self.version_title

    @property
    def title(self):
        if self.version_title:
            return self.complete_version_title
        if self.recording_title:
            return self.complete_recording_title
        return self.work.title

    @property
    def recording_id(self):
        if self._recording_id:
            return self._recording_id
        if self.id is None:
            return ""
        return "{}{:06}R".format(settings.PUBLISHER_CODE, self.id)

    @recording_id.setter
    def recording_id(self, value):
        if self._recording_id is not None:
            raise NotImplementedError("recording_id can not be changed")
        if value:
            self._recording_id = value

    def __str__(self):
        if self.artist:
            return "{}: {} ({})".format(self.recording_id, self.title, self.artist)
        return "{}: {}".format(self.recording_id, self.title)

    def get_dict(self, with_releases=False, with_work=True):
        recording_title = self.complete_recording_title or self.work.title
        date = self.release_date.strftime("%Y%m%d") if self.release_date else None
        duration = duration_string(self.duration) if self.duration else None
        artist = self.artist.get_dict() if self.artist else None
        label = self.record_label.get_dict() if self.record_label else None
        data = {
            "id": self.id,
            "code": self.recording_id,
            "recording_title": recording_title,
            "version_title": self.complete_version_title,
            "release_date": date,
            "duration": duration,
            "isrc": self.isrc,
            "recording_artist": artist,
            "record_label": label,
        }
        if with_releases:
            data["tracks"] = [
                {"release": track.release.get_dict(), "cut_number": track.cut_number}
                for track in self.tracks.all()
            ]
        if with_work:
            data["works"] = [{"work": self.work.get_dict(with_recordings=False)}]
        return data


class Track(models.Model):
    class Meta:
        verbose_name = "Track"
        indexes = [models.Index(fields=["recording", "release"]), models.Index(fields=["release", "cut_number"])]
        ordering = ("release", "cut_number")

    recording = models.ForeignKey(Recording, on_delete=models.PROTECT, related_name="tracks")
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="tracks")
    cut_number = models.PositiveSmallIntegerField(blank=True, null=True, validators=(MinValueValidator(1), MaxValueValidator(9999)))

    def get_dict(self):
        return {
            "cut_number": self.cut_number,
            "recording": self.recording.get_dict(with_releases=False, with_work=True),
        }

    def __str__(self):
        return self.recording.title


class DeferCwrManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().defer("cwr")


class CWRExport(models.Model):
    """Export in CWR format."""

    class Meta:
        verbose_name = "CWR Export"
        verbose_name_plural = "CWR Exports"
        ordering = ("-id",)

    objects = DeferCwrManager()

    nwr_rev = models.CharField(
        "CWR version/type",
        max_length=3,
        db_index=True,
        default="NWR",
        choices=(
            ("NWR", "CWR 2.1: New work registrations"),
            ("REV", "CWR 2.1: Revisions of registered works"),
            ("NW2", "CWR 2.2: New work registrations"),
            ("RE2", "CWR 2.2: Revisions of registered works"),
            ("WRK", "CWR 3.0: Work registration"),
            ("ISR", "CWR 3.0: ISWC request"),
            ("WR1", "CWR 3.1: Work registration"),
            ("IS1", "CWR 3.1: ISWC request"),
        ),
    )
    cwr = models.TextField(blank=True, editable=False)
    created_on = models.DateTimeField(editable=False, null=True)
    year = models.CharField(max_length=2, db_index=True, editable=False, blank=True)
    num_in_year = models.PositiveSmallIntegerField(default=0)
    works = models.ManyToManyField(Work, related_name="cwr_exports")
    description = models.CharField("Internal Note", blank=True, max_length=60)

    publisher_code = None
    agreement_pr = settings.PUBLISHING_AGREEMENT_PUBLISHER_PR
    agreement_mr = settings.PUBLISHING_AGREEMENT_PUBLISHER_MR
    agreement_sr = settings.PUBLISHING_AGREEMENT_PUBLISHER_SR

    @property
    def version(self):
        if self.nwr_rev in ["WRK", "ISR"]:
            return "30"
        if self.nwr_rev in ["WR1", "IS1"]:
            return "31"
        if self.nwr_rev in ["NW2", "RE2"]:
            return "22"
        return "21"

    @property
    def filename(self):
        if self.version in ["30", "31"]:
            return self.filename3
        return self.filename2

    @property
    def filename3(self):
        minor_version = "0-0" if self.version == "30" else "1-0"
        ext = "ISR" if self.nwr_rev == "ISR" else "SUB"
        return "CW{}{:04}{}_0000_V3-{}.{}".format(
            self.year,
            self.num_in_year,
            self.publisher_code or settings.PUBLISHER_CODE,
            minor_version,
            ext,
        )

    @property
    def filename2(self):
        return "CW{}{:04}{}_{}.V{}".format(
            self.year,
            self.num_in_year,
            self.publisher_code or settings.PUBLISHER_CODE,
            getattr(settings, "CWR_RECEIVER_CODE", "061"),
            self.version,
        )

    def __str__(self):
        return self.filename

    def get_record(self, key, record):
        if self.version == "30":
            template = TEMPLATES_30.get(key)
        elif self.version == "31":
            template = TEMPLATES_31.get(key)
        else:
            tdict = TEMPLATES_22 if self.version == "22" else TEMPLATES_21
            if key == "HDR" and len(record["ipi_name_number"].lstrip("0")) > 9:
                template = tdict.get("HDR_8")
            else:
                template = tdict.get(key)
        if not template:
            return ""
        record.update({"settings": settings})
        return template.render(Context(record)).upper()

    def get_transaction_record(self, key, record):
        record["transaction_sequence"] = self.transaction_count
        record["record_sequence"] = self.record_sequence
        line = self.get_record(key, record)
        if line:
            self.record_count += 1
            self.record_sequence += 1
        return line

    def yield_iswc_request_lines(self, works):
        for work in works:
            self.record_sequence = 0
            if work["iswc"]:
                work["indicator"] = "U"
            yield self.get_transaction_record("ISR", work)
            self.transaction_count += 1

    def _cwr_party_code(self, value):
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        digits = digits.lstrip("0")
        if not digits:
            return ""
        return digits[:9]

    def _party_with_societies_and_cwr_code(self, party):
        party = dict(party or {})
        party.setdefault("pr_society", "")
        party.setdefault("mr_society", "")
        party.setdefault("sr_society", "")
        for aff in party.get("affiliations", []):
            affiliation_type = aff.get("affiliation_type", {}).get("code")
            organization_code = aff.get("organization", {}).get("code")
            if affiliation_type == "PR":
                party["pr_society"] = organization_code
            elif affiliation_type == "MR":
                party["mr_society"] = organization_code
            elif affiliation_type == "SR":
                party["sr_society"] = organization_code
        party["cwr_code"] = self._cwr_party_code(
            party.get("ipi_name_number") or party.get("code")
        )
        party["tax_id"] = " " * 9
        return party

    def _publisher_with_societies(self, publisher):
        return self._party_with_societies_and_cwr_code(publisher)

    def _sadaic_original_publisher(self):
        return {
            "name": settings.ORIGINAL_PUBLISHER_NAME,
            "code": settings.ORIGINAL_PUBLISHER_CODE,
            "cwr_code": self._cwr_party_code(settings.ORIGINAL_PUBLISHER_IPI_NAME),
            "ipi_name_number": settings.ORIGINAL_PUBLISHER_IPI_NAME,
            "ipi_base_number": settings.ORIGINAL_PUBLISHER_IPI_BASE,
            "pr_society": settings.ORIGINAL_PUBLISHER_SOCIETY_PR,
            "mr_society": settings.ORIGINAL_PUBLISHER_SOCIETY_MR,
            "sr_society": settings.ORIGINAL_PUBLISHER_SOCIETY_SR,
            "tax_id": " " * 9,
        }

    def _sadaic_territory_data(self):
        return {
            "territory_code": getattr(settings, "CWR_TERRITORY_CODE", "0032"),
            "shares_change": getattr(settings, "CWR_SHARES_CHANGE_FLAG", " "),
            "territory_sequence": "001",
        }

    def yield_publisher_lines(self, publisher, controlled_relative_share):
        publisher = self._publisher_with_societies(publisher)
        collection_pr_share = controlled_relative_share * self.agreement_pr
        collection_mr_share = controlled_relative_share * self.agreement_mr
        collection_sr_share = controlled_relative_share * self.agreement_sr

        if getattr(settings, "SADAIC_CWR_MODE", False):
            original_publisher = self._sadaic_original_publisher()

            if getattr(settings, "SADAIC_ZERO_OWNERSHIP_SHARES", True):
                ownership_pr_share = Decimal(0)
                ownership_mr_share = Decimal(0)
                ownership_sr_share = Decimal(0)
            else:
                ownership_pr_share = collection_pr_share
                ownership_mr_share = collection_mr_share
                ownership_sr_share = collection_sr_share

            # SPU 1: MARMAZ PUBLISHING / E / chain 01.
            yield self.get_transaction_record(
                "SPU",
                {
                    "chain_sequence": 1,
                    "code": original_publisher["cwr_code"],
                    "cwr_code": original_publisher["cwr_code"],
                    "name": original_publisher["name"],
                    "role": "E ",
                    "tax_id": original_publisher["tax_id"],
                    "ipi_name_number": original_publisher["ipi_name_number"],
                    "ipi_base_number": original_publisher["ipi_base_number"],
                    "pr_society": original_publisher["pr_society"],
                    "mr_society": original_publisher["mr_society"],
                    "sr_society": original_publisher["sr_society"],
                    "pr_share": ownership_pr_share,
                    "mr_share": ownership_mr_share,
                    "sr_share": ownership_sr_share,
                },
            )

            # SPU 2: CORPORACION MARMAZ SAS / SE / same chain 01.
            yield self.get_transaction_record(
                "SPU",
                {
                    "chain_sequence": 1,
                    "code": publisher["cwr_code"],
                    "cwr_code": publisher["cwr_code"],
                    "name": publisher.get("name"),
                    "role": "SE",
                    "tax_id": publisher.get("tax_id", " " * 9),
                    "ipi_name_number": publisher.get("ipi_name_number"),
                    "ipi_base_number": publisher.get("ipi_base_number"),
                    "pr_society": publisher.get("pr_society"),
                    "mr_society": publisher.get("mr_society"),
                    "sr_society": publisher.get("sr_society"),
                    "pr_share": Decimal(0),
                    "mr_share": Decimal(0),
                    "sr_share": Decimal(0),
                },
            )

            if controlled_relative_share:
                spt_data = {
                    "code": publisher["cwr_code"],
                    "cwr_code": publisher["cwr_code"],
                    "collection_pr_share": collection_pr_share,
                    "collection_mr_share": collection_mr_share,
                    "collection_sr_share": collection_sr_share,
                }
                spt_data.update(self._sadaic_territory_data())
                yield self.get_transaction_record("SPT", spt_data)
            return

        yield self.get_transaction_record(
            "SPU",
            {
                "chain_sequence": 1,
                "name": publisher.get("name"),
                "code": "P000001",
                "role": "E ",
                "ipi_name_number": publisher.get("ipi_name_number"),
                "ipi_base_number": publisher.get("ipi_base_number"),
                "pr_society": publisher.get("pr_society"),
                "mr_society": publisher.get("mr_society"),
                "sr_society": publisher.get("sr_society"),
                "pr_share": collection_pr_share,
                "mr_share": collection_mr_share,
                "sr_share": collection_sr_share,
            },
        )
        if controlled_relative_share:
            yield self.get_transaction_record(
                "SPT",
                {
                    "code": "P000001",
                    "pr_share": collection_pr_share,
                    "mr_share": collection_mr_share,
                    "sr_share": collection_sr_share,
                },
            )

    def yield_registration_lines(self, works):
        for work in works:
            self.record_sequence = 0
            if self.version == "22":
                record_type = "NWR" if self.nwr_rev == "NW2" else "REV"
            else:
                record_type = self.nwr_rev
            indicator = "Y" if work["recordings"] else "U"
            version_type = "MOD   UNSUNS" if work["version_type"]["code"] == "MOD" else "ORI         "
            d = {
                "record_type": record_type,
                "code": work["code"],
                "work_title": work["work_title"],
                "iswc": work["iswc"],
                "recorded_indicator": indicator,
                "version_type": version_type,
            }
            yield self.get_transaction_record("WRK", d)
            yield from self.get_party_lines(work)
            yield from self.get_other_lines(work)
            self.transaction_count += 1

    def yield_other_publisher_lines(self, other_publisher_share):
        if other_publisher_share:
            pr_share = other_publisher_share * self.agreement_pr
            mr_share = other_publisher_share * self.agreement_mr
            sr_share = other_publisher_share * self.agreement_sr
            yield self.get_transaction_record("OPU", {"sequence": 2, "pr_share": pr_share, "mr_share": mr_share, "sr_share": sr_share})
            yield self.get_transaction_record("OPT", {"pr_share": pr_share, "mr_share": mr_share, "sr_share": sr_share})

    def calculate_publisher_shares(self, work):
        controlled_relative_share = Decimal(0)
        other_publisher_share = Decimal(0)
        controlled_writer_ids = set()
        copublished_writer_ids = set()
        controlled_shares = defaultdict(Decimal)
        for wiw in work["writers"]:
            if wiw["controlled"]:
                controlled_writer_ids.add(wiw["writer"]["code"])
        for wiw in work["writers"]:
            writer = wiw["writer"]
            share = Decimal(wiw["relative_share"])
            if wiw["controlled"]:
                key = writer["code"]
                controlled_relative_share += share
                controlled_shares[key] += share
            elif writer and writer["code"] in controlled_writer_ids:
                key = writer["code"]
                copublished_writer_ids.add(key)
                other_publisher_share += share
                controlled_shares[key] += share
        return controlled_relative_share, other_publisher_share, controlled_shares, controlled_writer_ids, copublished_writer_ids

    def yield_controlled_writer_lines(self, work, publisher, controlled_shares, copublished_writer_ids, other_publisher_share):
        reported_writers = set()
        for wiw in work["writers"]:
            if not wiw["controlled"]:
                continue
            w = self._party_with_societies_and_cwr_code(wiw["writer"])
            writer_key = w.get("ipi_name_number") or w.get("code")
            if writer_key in reported_writers:
                continue
            reported_writers.add(writer_key)
            agr = wiw["original_publishers"][0]["agreement"] if wiw["original_publishers"] else None
            saan = agr["recipient_agreement_number"] if agr else None
            share = controlled_shares[w["code"]]
            collection_pr_share = share * (1 - self.agreement_pr)
            collection_mr_share = share * (1 - self.agreement_mr)
            collection_sr_share = share * (1 - self.agreement_sr)
            if getattr(settings, "SADAIC_ZERO_OWNERSHIP_SHARES", False):
                pr_share = Decimal(0)
                mr_share = Decimal(0)
                sr_share = Decimal(0)
            else:
                pr_share = collection_pr_share
                mr_share = collection_mr_share
                sr_share = collection_sr_share
            w.update(
                {
                    "writer_role": wiw["writer_role"]["code"],
                    "share": share,
                    "pr_share": pr_share,
                    "mr_share": mr_share,
                    "sr_share": sr_share,
                    "collection_pr_share": collection_pr_share,
                    "collection_mr_share": collection_mr_share,
                    "collection_sr_share": collection_sr_share,
                    "saan": saan,
                    "original_publishers": wiw["original_publishers"],
                }
            )
            w.update(self._sadaic_territory_data())
            yield self.get_transaction_record("SWR", w)
            if share:
                yield self.get_transaction_record("SWT", w)
                yield self.get_transaction_record("MAN", w)
                if getattr(settings, "SADAIC_CWR_MODE", False):
                    original_publisher = self._sadaic_original_publisher()
                    w["publisher_sequence"] = 1
                    w["publisher_code"] = original_publisher["cwr_code"]
                    w["publisher_cwr_code"] = original_publisher["cwr_code"]
                    w["publisher_name"] = original_publisher["name"]
                    w["submitter_agreement_number"] = getattr(settings, "SADAIC_PWR_SUBMITTER_AGREEMENT", "1")
                    w["society_assigned_agreement_number"] = ""
                else:
                    w["publisher_sequence"] = 1
                    w["publisher_code"] = "P000001"
                    w["publisher_name"] = publisher["name"]
                    w["submitter_agreement_number"] = saan or ""
                yield self.get_transaction_record("PWR", w)
            copublished = self.version in ["30", "31"] and other_publisher_share and w and w["code"] in copublished_writer_ids
            if copublished:
                w["publisher_sequence"] = 2
                yield self.get_transaction_record("PWR", {"code": w["code"], "publisher_sequence": 2})

    def yield_other_writer_lines(self, work, controlled_writer_ids, other_publisher_share):
        for wiw in work["writers"]:
            if wiw["controlled"]:
                continue
            writer = wiw["writer"]
            if writer and writer["code"] in controlled_writer_ids:
                continue
            if writer:
                w = self._party_with_societies_and_cwr_code(writer)
            else:
                w = {"writer_unknown_indicator": "Y", "tax_id": " " * 9, "cwr_code": ""}
            share = Decimal(wiw["relative_share"])
            w.update(
                {
                    "writer_role": wiw["writer_role"]["code"] if wiw["writer_role"] else None,
                    "share": share,
                    "pr_share": share,
                    "mr_share": share,
                    "sr_share": share,
                    "collection_pr_share": share,
                    "collection_mr_share": share,
                    "collection_sr_share": share,
                }
            )
            w.update(self._sadaic_territory_data())
            yield self.get_transaction_record("OWR", w)
            if w["share"]:
                yield self.get_transaction_record("OWT", w)
                yield self.get_transaction_record("MAN", w)
            if self.version in ["30", "31"] and other_publisher_share:
                w["publisher_sequence"] = 2
                yield self.get_transaction_record("PWR", w)

    def get_party_lines(self, work):
        controlled_relative_share, other_publisher_share, controlled_shares, controlled_writer_ids, copublished_writer_ids = self.calculate_publisher_shares(work)
        publisher = work["writers"][0]["original_publishers"][0]["publisher"]
        yield from self.yield_publisher_lines(publisher, controlled_relative_share)
        yield from self.yield_other_publisher_lines(other_publisher_share)
        yield from self.yield_controlled_writer_lines(work, publisher, controlled_shares, copublished_writer_ids, other_publisher_share)
        yield from self.yield_other_writer_lines(work, controlled_writer_ids, other_publisher_share)

    def get_alt_lines(self, work):
        alt_titles = set()
        for at in work["other_titles"]:
            alt_titles.add((at["title"], at["title_type"]["code"]))
        for rec in work["recordings"]:
            if rec["recording_title"]:
                alt_titles.add((rec["recording_title"], "AT"))
            if rec["version_title"]:
                alt_titles.add((rec["version_title"], "AT"))
        for alt_title, title_type in sorted(alt_titles, key=lambda x: x[0]):
            if alt_title == work["work_title"]:
                continue
            yield self.get_transaction_record("ALT", {"alternate_title": alt_title, "title_type": title_type})

    def get_per_lines(self, work):
        artists = {}
        for aiw in work["performing_artists"]:
            artists.update({aiw["artist"]["code"]: aiw["artist"]})
        for rec in work["recordings"]:
            if rec["recording_artist"]:
                artists.update({rec["recording_artist"]["code"]: rec["recording_artist"]})
        for artist in artists.values():
            yield self.get_transaction_record("PER", artist)

    def get_rec_lines(self, work):
        if getattr(settings, "SADAIC_SKIP_REC", False):
            return
        for rec in work["recordings"]:
            if rec["recording_artist"]:
                rec["display_artist"] = "{} {}".format(
                    rec["recording_artist"]["first_name"] or "",
                    rec["recording_artist"]["last_name"],
                ).strip()[:60]
            if rec["isrc"]:
                rec["isrc_validity"] = "Y"
            if rec["duration"]:
                rec["duration"] = rec["duration"].replace(":", "")[0:6]
            empty = not any([rec["release_date"], rec["duration"], rec["isrc"]])
            if self.version in ["21", "22"] and empty:
                continue
            yield self.get_transaction_record("REC", rec)

    def get_other_lines(self, work):
        yield from self.get_alt_lines(work)
        if work["version_type"]["code"] == "MOD" and work["original_works"]:
            yield self.get_transaction_record("OWK", work["original_works"][0])
        yield from self.get_per_lines(work)
        yield from self.get_rec_lines(work)
        if work["origin"]:
            yield self.get_transaction_record("ORN", {"library": work["origin"]["library"]["name"], "cd_identifier": work["origin"]["cd_identifier"]})
        for xrf in work["cross_references"]:
            yield self.get_transaction_record("XRF", xrf)

    def get_header(self):
        return self.get_record(
            "HDR",
            {
                "creation_date": datetime.now(),
                "filename": self.filename,
                "ipi_name_number": settings.PUBLISHER_IPI_NAME,
                "name": settings.PUBLISHER_NAME,
                "code": settings.PUBLISHER_CODE,
            },
        )

    def yield_lines(self, works):
        self.record_count = self.record_sequence = self.transaction_count = 0
        yield self.get_header()
        if self.nwr_rev == "NW2":
            yield self.get_record("GRH", {"transaction_type": "NWR"})
        elif self.nwr_rev == "RE2":
            yield self.get_record("GRH", {"transaction_type": "REV"})
        else:
            yield self.get_record("GRH", {"transaction_type": self.nwr_rev})
        lines = self.yield_iswc_request_lines(works) if self.nwr_rev == "ISR" else self.yield_registration_lines(works)
        for line in lines:
            yield line
        yield self.get_record("GRT", {"transaction_count": self.transaction_count, "record_count": self.record_count + 2})
        yield self.get_record("TRL", {"transaction_count": self.transaction_count, "record_count": self.record_count + 4})

    def create_cwr(self, publisher_code=None):
        now = timezone.now()
        if publisher_code is None:
            publisher_code = settings.PUBLISHER_CODE
        self.publisher_code = publisher_code
        if self.cwr:
            return
        self.created_on = now
        self.year = now.strftime("%y")
        last = type(self).objects.filter(year=self.year).order_by("-num_in_year").first()
        self.num_in_year = last.num_in_year + 1 if last else 1
        qs = self.works.order_by("id")
        works = Work.objects.get_dict(qs)["works"]
        self.cwr = "".join(self.yield_lines(works))
        self.save()
        Work.persist_work_ids(self.works)


class WorkAcknowledgement(models.Model):
    class Meta:
        verbose_name = "Registration Acknowledgement"
        ordering = ("-date", "-id")
        indexes = [models.Index(fields=["society_code", "remote_work_id"])]

    TRANSACTION_STATUS_CHOICES = (
        ("CO", "Conflict"),
        ("DU", "Duplicate"),
        ("RA", "Transaction Accepted"),
        ("AS", "Registration Accepted"),
        ("AC", "Registration Accepted with Changes"),
        ("SR", "Registration Accepted - Ready for Payment"),
        ("CR", "Registration Accepted with Changes - Ready for Payment"),
        ("RJ", "Rejected"),
        ("NP", "No Participation"),
        ("RC", "Claim rejected"),
        ("NA", "Rejected - No Society Agreement Number"),
        ("WA", "Rejected - Wrong Society Agreement Number"),
    )

    work = models.ForeignKey(Work, on_delete=models.PROTECT)
    society_code = models.CharField("Society", max_length=3, choices=SOCIETIES)
    date = models.DateField()
    status = models.CharField(max_length=2, choices=TRANSACTION_STATUS_CHOICES)
    remote_work_id = models.CharField("Remote work ID", max_length=20, blank=True, db_index=True)

    def get_dict(self):
        return {
            "organization": {
                "code": self.society_code,
                "name": self.get_society_code_display().split(",")[0],
            },
            "identifier": self.remote_work_id,
        }


class ACKImport(models.Model):
    """CWR acknowledgement file import."""

    class Meta:
        verbose_name = "ACK Import"
        verbose_name_plural = "ACK Imports"
        ordering = ("-date", "-id")

    filename = models.CharField(max_length=255, blank=True)
    society_code = models.CharField(max_length=3, blank=True)
    society_name = models.CharField(max_length=45, blank=True)
    date = models.DateField(blank=True, null=True)
    acknowledgement_file = models.TextField(blank=True)
    report = models.TextField(blank=True)
    imported_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename or "ACK Import"

    def import_acknowledgement(self, import_iswcs=True):
        self.report = self.report or "ACK import saved."
        self.save()
        return self.report


class DataImport(models.Model):
    """CSV data import report."""

    class Meta:
        verbose_name = "Data Import"
        verbose_name_plural = "Data Imports"
        ordering = ("-created_on", "-id")

    created_on = models.DateTimeField(auto_now_add=True)
    data_file = models.FileField(upload_to=upload_to, max_length=255, blank=True)
    report = models.TextField(blank=True)

    def __str__(self):
        return "Data import {}".format(self.created_on or self.id)


@receiver(pre_save, sender=Work)
def work_pre_save(sender, instance, **kwargs):
    instance.last_change = timezone.now()


@receiver(pre_save, sender=WriterInWork)
@receiver(pre_save, sender=ArtistInWork)
@receiver(pre_save, sender=AlternateTitle)
def work_related_pre_save(sender, instance, **kwargs):
    if instance.work_id:
        Work.objects.filter(pk=instance.work_id).update(last_change=timezone.now())


@receiver(pre_save, sender=Recording)
def recording_pre_save(sender, instance, **kwargs):
    if instance.work_id:
        Work.objects.filter(pk=instance.work_id).update(last_change=timezone.now())


@receiver(pre_save, sender=Track)
def track_pre_save(sender, instance, **kwargs):
    if instance.recording_id and instance.recording.work_id:
        Work.objects.filter(pk=instance.recording.work_id).update(last_change=timezone.now())

