import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatListModule } from '@angular/material/list';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './pages/login/login.component';
import { UploadComponent } from './pages/upload/upload.component';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { EvaluationDetailComponent } from './pages/evaluation-detail/evaluation-detail.component';
import { TextbooksComponent } from './pages/textbooks/textbooks.component';
import { InsightsComponent } from './pages/insights/insights.component';
import { StudyPlanPageComponent } from './pages/study-plan/study-plan.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    UploadComponent,
    DashboardComponent,
    EvaluationDetailComponent,
    TextbooksComponent,
    InsightsComponent,
    StudyPlanPageComponent,
  ],
  imports: [
    BrowserModule,
    CommonModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    AppRoutingModule,
    MatToolbarModule,
    MatButtonModule,
    MatCardModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    MatTableModule,
    MatSelectModule,
    MatExpansionModule,
    MatListModule,
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
