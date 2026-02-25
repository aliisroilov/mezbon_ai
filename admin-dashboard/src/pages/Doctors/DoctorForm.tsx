import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { doctorsAPI } from "../../api/client";
import { Input, Select, Textarea, Button } from "../../components/ui";
import type { Doctor, Department } from "../../types";

const schema = z.object({
  full_name: z.string().min(2, "Name is required"),
  specialty: z.string().min(2, "Specialty is required"),
  department_id: z.string().min(1, "Department is required"),
  bio: z.string().optional(),
  is_active: z.boolean(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  doctor: Doctor | null;
  departments: Department[];
  onSuccess: () => void;
}

export function DoctorForm({ doctor, departments, onSuccess }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: doctor?.full_name ?? "",
      specialty: doctor?.specialty ?? "",
      department_id: doctor?.department_id ?? "",
      bio: doctor?.bio ?? "",
      is_active: doctor?.is_active ?? true,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      doctor
        ? doctorsAPI.update(doctor.id, data)
        : doctorsAPI.create(data),
    onSuccess,
  });

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
      <Input
        label="Full Name"
        {...register("full_name")}
        error={errors.full_name?.message}
      />
      <Input
        label="Specialty"
        {...register("specialty")}
        error={errors.specialty?.message}
      />
      <Select
        label="Department"
        {...register("department_id")}
        error={errors.department_id?.message}
        options={[
          { value: "", label: "Select department..." },
          ...departments.map((d) => ({ value: d.id, label: d.name })),
        ]}
      />
      <Textarea
        label="Bio"
        {...register("bio")}
        rows={3}
        placeholder="Brief doctor biography..."
      />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...register("is_active")} className="rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
        Active
      </label>

      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <Button type="submit" loading={mutation.isPending}>
          {doctor ? "Update" : "Create"} Doctor
        </Button>
      </div>
    </form>
  );
}
