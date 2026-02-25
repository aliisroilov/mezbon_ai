import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { patientsAPI } from "../../api/client";
import { Input, Select, Button } from "../../components/ui";

const schema = z.object({
  full_name: z.string().min(2, "Name is required"),
  phone: z.string().min(9, "Valid phone required"),
  date_of_birth: z.string().optional(),
  language_preference: z.enum(["uz", "ru", "en"]),
});

type FormData = z.infer<typeof schema>;

interface Props {
  onSuccess: () => void;
}

export function PatientForm({ onSuccess }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: "",
      phone: "",
      date_of_birth: "",
      language_preference: "uz",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) => patientsAPI.create(data),
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
        label="Phone"
        {...register("phone")}
        error={errors.phone?.message}
        placeholder="+998 XX XXX XX XX"
      />
      <Input
        label="Date of Birth"
        type="date"
        {...register("date_of_birth")}
      />
      <Select
        label="Language"
        {...register("language_preference")}
        options={[
          { value: "uz", label: "Uzbek" },
          { value: "ru", label: "Russian" },
          { value: "en", label: "English" },
        ]}
      />

      {mutation.error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {(mutation.error as Error).message}
        </div>
      )}

      <div className="flex justify-end pt-2">
        <Button type="submit" loading={mutation.isPending}>
          Register Patient
        </Button>
      </div>
    </form>
  );
}
