import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../services/api.service';
import { UploadService } from '../../services/upload.service';
import { TextbookOut } from '../../models/api.models';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-textbooks',
  templateUrl: './textbooks.component.html',
  styleUrls: ['./textbooks.component.scss'],
})
export class TextbooksComponent implements OnInit {
  textbooks: TextbookOut[] = [];
  loading = true;
  uploading = false;

  form: FormGroup;
  selectedFile: File | null = null;

  readonly displayedColumns = ['title', 'indexed', 'date'];

  constructor(
    private fb: FormBuilder,
    private api: ApiService,
    private uploadSvc: UploadService,
    private snack: MatSnackBar
  ) {
    this.form = this.fb.group({ title: ['', Validators.required] });
  }

  ngOnInit(): void {
    this.loadTextbooks();
  }

  loadTextbooks(): void {
    this.loading = true;
    this.api.getTextbooks().subscribe({
      next: (list) => {
        this.textbooks = list;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snack.open('Failed to load textbooks.', 'Dismiss', { duration: 4000 });
      },
    });
  }

  onFile(e: Event): void {
    this.selectedFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  upload(): void {
    if (this.form.invalid || !this.selectedFile) return;
    this.uploading = true;
    this.uploadSvc
      .uploadTextbook(this.selectedFile, this.form.value.title)
      .pipe(finalize(() => (this.uploading = false)))
      .subscribe({
        next: () => {
          this.snack.open('Textbook uploaded and indexed!', 'OK', { duration: 3000 });
          this.form.reset();
          this.selectedFile = null;
          this.loadTextbooks();
        },
        error: () => this.snack.open('Upload failed.', 'Dismiss', { duration: 4000 }),
      });
  }
}
